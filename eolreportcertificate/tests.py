#!/usr/bin/env python
# -*- coding: utf-8 -*-
from mock import patch, Mock, MagicMock
from collections import namedtuple
from django.urls import reverse
from django.test import TestCase, Client
from django.test import Client
from django.conf import settings
from django.contrib.auth.models import User
from opaque_keys.edx.locator import CourseLocator
from common.djangoapps.student.tests.factories import CourseEnrollmentAllowedFactory, UserFactory, CourseEnrollmentFactory
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from common.djangoapps.student.roles import CourseInstructorRole, CourseStaffRole
from .views import EolReportCertificateView, task_get_data
from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
from common.djangoapps.student.tests.factories import CourseAccessRoleFactory
from lms.djangoapps.instructor_task.models import ReportStore
from lms.djangoapps.certificates.models import GeneratedCertificate
from uchileedxlogin.models import EdxLoginUser
from unittest.case import SkipTest
import urllib
import json

class TestEolReportCertificateView(ModuleStoreTestCase):
    def setUp(self):
        super(TestEolReportCertificateView, self).setUp()
        self.course = CourseFactory.create(
            org='mss',
            course='999',
            display_name='2021',
            emit_signals=True)
        aux = CourseOverview.get_from_id(self.course.id)
        with patch('common.djangoapps.student.models.cc.User.save'):
            # staff user
            self.client_instructor = Client()
            self.client_student = Client()
            self.client_anonymous = Client()
            self.user_instructor = UserFactory(
                username='instructor',
                password='12345',
                email='instructor@edx.org')
            role = CourseInstructorRole(self.course.id)
            role.add_users(self.user_instructor)
            self.client_instructor.login(
                username='instructor', password='12345')
            self.user_staff_role = UserFactory(
                username='staff_role',
                password='12345',
                email='staff_role@edx.org')
            role2 = CourseStaffRole(self.course.id)
            role2.add_users(self.user_staff_role)
            self.student = UserFactory(
                username='student',
                password='test',
                email='student@edx.org')
            EdxLoginUser.objects.create(user=self.student, run='09472337K')
            self.gc1 = GeneratedCertificate.objects.create(user=self.student, course_id=self.course.id, verify_uuid='12350e8c6d464bb395a1fb39013ba4f4', status='downloadable', mode='honor')
            self.student_2 = UserFactory(
                username='student_2',
                password='test',
                email='student2@edx.org')
            self.gc2 = GeneratedCertificate.objects.create(user=self.student_2, course_id=self.course.id, verify_uuid='45650e8c6d464bb395a1fb39013ba4f4', status='downloadable', mode='honor')
            self.student_3 = UserFactory(
                username='student_3',
                password='test',
                email='student3@edx.org')
            GeneratedCertificate.objects.create(user=self.student_3, course_id=self.course.id, verify_uuid='78950e8c6d464bb395a1fb39013ba4f4', status='unavailable', mode='honor')
            # Enroll the student in the course
            CourseEnrollmentFactory(
                user=self.student, course_id=self.course.id, mode='honor')
            CourseEnrollmentFactory(
                user=self.student_2, course_id=self.course.id, mode='honor')
            CourseEnrollmentFactory(
                user=self.student_3, course_id=self.course.id, mode='honor')
            self.client_student.login(
                username='student', password='test')
            # Create and Enroll data researcher user
            self.data_researcher_user = UserFactory(
                username='data_researcher_user',
                password='test',
                email='data.researcher@edx.org')
            CourseEnrollmentFactory(
                user=self.data_researcher_user,
                course_id=self.course.id, mode='audit')
            CourseAccessRoleFactory(
                course_id=self.course.id,
                user=self.data_researcher_user,
                role='data_researcher',
                org=self.course.id.org
            )
            self.client_data_researcher = Client()
            self.assertTrue(self.client_data_researcher.login(username='data_researcher_user', password='test'))
    
    def _verify_csv_file_report(self, report_store, expected_data):
        """
        Verify course survey data.
        """
        report_csv_filename = report_store.links_for(self.course.id)[0][0]
        report_path = report_store.path_to(self.course.id, report_csv_filename)
        with report_store.storage.open(report_path) as csv_file:
            csv_file_data = csv_file.read()
            # Removing unicode signature (BOM) from the beginning
            csv_file_data = csv_file_data.decode("utf-8-sig")
            for data in expected_data:
                self.assertIn(data, csv_file_data)
    
    def _verify_csv_file_report_not_in(self, report_store, expected_data):
        """
        Verify course survey data.
        """
        report_csv_filename = report_store.links_for(self.course.id)[0][0]
        report_path = report_store.path_to(self.course.id, report_csv_filename)
        with report_store.storage.open(report_path) as csv_file:
            csv_file_data = csv_file.read()
            # Removing unicode signature (BOM) from the beginning
            csv_file_data = csv_file_data.decode("utf-8-sig")
            for data in expected_data:
                self.assertNotIn(data, csv_file_data)

    def test_eolreportcertificate_post(self):
        """
            Test eolreportcertificate view
        """
        response = self.client_instructor.post('{}?{}'.format(reverse('eolreportcertificate-export:data'), urllib.parse.urlencode({'course': str(self.course.id)})))
        request = response.request
        self.assertEqual(response.status_code, 405)

    def test_eolreportcertificate_get(self):
        """
            Test eolreportcertificate get normal process
        """
        task_input = {'base_url': 'this_is_a_url'}
        with patch('lms.djangoapps.instructor_task.tasks_helper.runner._get_current_task'):
            result = task_get_data(
                None, None, self.course.id,
                task_input, 'EOL_REPORT_CERTIFICATE'
            )
        report_store = ReportStore.from_config(config_name='GRADES_DOWNLOAD')
        header_row = ",".join(['Username', 'Run', 'Email', 'Modo', 'Url'])
        student1_row = ",".join([
            self.student.username,
            self.student.edxloginuser.run,
            self.student.email,
            self.gc1.mode,
            '{}{}'.format(task_input['base_url'], reverse('certificates:render_cert_by_uuid', kwargs={'certificate_uuid': self.gc1.verify_uuid}))
        ])
        student2_row = ",".join([
            self.student_2.username,
            '',
            self.student_2.email,
            self.gc2.mode,
            '{}{}'.format(task_input['base_url'], reverse('certificates:render_cert_by_uuid', kwargs={'certificate_uuid':self.gc2.verify_uuid}))
        ])
        student3_row = ",".join([
            self.student_3.username,
            '',
            self.student_3.email,
            ''
        ])
        expected_data = [header_row, student1_row, student2_row]
        self._verify_csv_file_report(report_store, expected_data)
        expected_data_2 = [student3_row]
        self._verify_csv_file_report_not_in(report_store, expected_data_2)

    def test_eolreportcertificate_no_course(self):
        """
            Test eolreportcertificate view when no course in get
        """
        url = reverse('eolreportcertificate-export:data')
        response = self.client_instructor.get(url)
        self.assertEqual(response.status_code, 200)
        r = json.loads(response._container[0].decode())
        self.assertEqual(r['status'], 'Error')
        self.assertEqual(r['empty_course'], True)

    def test_eolreportcertificate_wrong_course(self):
        """
            Test eolreportcertificate view when course does not exists or is wrong
        """
        url = '{}?{}'.format(reverse('eolreportcertificate-export:data'), urllib.parse.urlencode({'course': 'course-v1:eol+Test101+2021'}))
        response = self.client_instructor.get(url)
        self.assertEqual(response.status_code, 200)
        r = json.loads(response._container[0].decode())
        self.assertEqual(r['status'], 'Error')
        self.assertEqual(r['error_curso'], True)

    def test_eolreportcertificate_no_permission(self):
        """
            Test eolreportcertificate view when user dont have permission or role
        """
        url = '{}?{}'.format(reverse('eolreportcertificate-export:data'), urllib.parse.urlencode({'course': str(self.course.id)}))
        response = self.client_student.get(url)
        self.assertEqual(response.status_code, 200)
        r = json.loads(response._container[0].decode())
        self.assertEqual(r['status'], 'Error')
        self.assertEqual(r['user_permission'], True)
    
    def test_eolreportcertificate_user_anonymous(self):
        """
            Test eolreportcertificate view when user is anonymous
        """
        url = '{}?{}'.format(reverse('eolreportcertificate-export:data'), urllib.parse.urlencode({'course': str(self.course.id)}))
        response = self.client_anonymous.get(url)
        self.assertEqual(response.status_code, 404)
    
    def test_eolreportcertificate_check_user_permission(self):
        """
            Test eolreportcertificate view, verify users permission
        """
        self.assertTrue(EolReportCertificateView().user_have_permission(self.user_instructor, str(self.course.id)))
        self.assertTrue(EolReportCertificateView().user_have_permission(self.data_researcher_user, str(self.course.id)))
        self.assertTrue(EolReportCertificateView().user_have_permission(self.user_staff_role, str(self.course.id)))
        self.assertFalse(EolReportCertificateView().user_have_permission(self.student, str(self.course.id)))
