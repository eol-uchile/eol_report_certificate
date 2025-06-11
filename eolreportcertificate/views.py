#!/usr/bin/env python
# -- coding: utf-8 --
# Python Standard Libraries
from datetime import datetime
from functools import partial
from time import time
import codecs
import csv
import logging

# Installed packages (via pip)
from celery import task
from django.contrib.auth.models import User
from django.core.exceptions import FieldError
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import Http404, JsonResponse
from django.urls import reverse
from django.utils.translation import ugettext_noop
from django.views.generic.base import View
from pytz import UTC
import six

# Edx dependencies
from common.djangoapps.util.file import course_filename_prefix_generator
from lms.djangoapps.courseware.access import has_access
from lms.djangoapps.courseware.courses import get_course_with_access
from lms.djangoapps.instructor import permissions
from lms.djangoapps.instructor_task.api_helper import AlreadyRunningError, submit_task
from lms.djangoapps.instructor_task.models import ReportStore
from lms.djangoapps.instructor_task.tasks_base import BaseInstructorTask
from lms.djangoapps.instructor_task.tasks_helper.runner import run_main_task, TaskProgress
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview

logger = logging.getLogger(__name__)

@task(base=BaseInstructorTask, queue='edx.lms.core.low')
def process_data(entry_id, xmodule_instance_args):
    action_name = ugettext_noop('generated')
    task_fn = partial(task_get_data, xmodule_instance_args)
    return run_main_task(entry_id, task_fn, action_name)

def task_get_data(
        _xmodule_instance_args,
        _entry_id,
        course_id,
        task_input,
        action_name):

    base_url = task_input['base_url']
    start_time = time()
    start_date = datetime.now(UTC)
    num_reports = 1
    task_progress = TaskProgress(action_name, num_reports, start_time)
    current_step = {'step': 'EolReportCertificate - Getting users data'}
    task_progress.update_task_state(extra_meta=current_step)

    students = EolReportCertificateView().get_all_enrolled_users(course_id, base_url)

    report_store = ReportStore.from_config('GRADES_DOWNLOAD')
    csv_name = 'Reporte_de_Certificados_Emitidos'

    report_name = u"{course_prefix}_{csv_name}_{timestamp_str}.csv".format(
        course_prefix=course_filename_prefix_generator(course_id),
        csv_name=csv_name,
        timestamp_str=start_date.strftime("%Y-%m-%d-%H%M")
    )
    output_buffer = ContentFile('')
    if six.PY2:
        output_buffer.write(codecs.BOM_UTF8)
    csvwriter = csv.writer(output_buffer)

    header = ['Username', 'Run', 'Email', 'Modo', 'Url']
    csvwriter.writerow(_get_utf8_encoded_row(header))
    csvwriter.writerows(ReportStore()._get_utf8_encoded_rows(students))

    current_step = {'step': 'EolReportCertificate - Uploading CSV'}
    task_progress.update_task_state(extra_meta=current_step)

    output_buffer.seek(0)
    report_store.store(course_id, report_name, output_buffer)
    current_step = {
        'step': 'EolReportCertificate - CSV uploaded',
        'report_name': report_name,
    }

    return task_progress.update_task_state(extra_meta=current_step)

def task_process_data(request, course_id):
    course_key = CourseKey.from_string(course_id)
    task_type = 'EOL_REPORT_CERTIFICATE'
    task_class = process_data
    task_input = {'base_url': request.build_absolute_uri('/')[0:-1]}
    task_key = "EOL_REPORT_CERTIFICATE_{}".format(course_id)

    return submit_task(
        request,
        task_type,
        task_class,
        course_key,
        task_input,
        task_key)

def _get_utf8_encoded_row(row):
    """
    Given a list of `rows` containing unicode strings, return a
    new list of rows with those strings encoded as utf-8 for CSV
    compatibility.
    """
    
    if six.PY2:
        return [six.text_type(item).encode('utf-8') for item in row]
    else:
        return [six.text_type(item) for item in row]

class EolReportCertificateView(View):
    """
    Return a csv of Issued Certificates.
    """
    @transaction.non_atomic_requests
    def dispatch(self, args, **kwargs):
        return super(EolReportCertificateView, self).dispatch(args, **kwargs)

    def get(self, request, **kwargs):
        if not request.user.is_anonymous:
            course_id = request.GET.get('course', "")
            data_error = self.validate_data(request.user, course_id)
            if len(data_error) == 0:
                return self.get_data_report(request, course_id)
            else:
                data_error['status'] = 'Error'
                return JsonResponse(data_error)
        else:
            logger.error("EolReportCertificate - User is Anonymous")
        raise Http404()

    def get_data_report(self, request, course_id):
        """
        Generate report with task_process.
        """
        try:
            task = task_process_data(request, course_id)
            success_status = 'Generating'
            return JsonResponse({"status": success_status, "task_id": task.task_id})
        except AlreadyRunningError:
            logger.error("EolReportCertificate - Task Already Running Error, user: {}, course_id: {}".format(request.user, course_id))
            return JsonResponse({'status': 'AlreadyRunningError'})

    def get_all_enrolled_users(self, course_key, base_url):
        """
        Get all enrolled student with Issued Certificates for course_key.
        """
        students = []
        try:
            enrolled_students = User.objects.filter(
                generatedcertificate__status='downloadable',
                generatedcertificate__course_id=course_key
            ).order_by('username').values('username', 'email', 'generatedcertificate__verify_uuid', 'generatedcertificate__mode', 'edxloginuser__run')
        except FieldError:
            enrolled_students = User.objects.filter(
                generatedcertificate__status='downloadable',
                generatedcertificate__course_id=course_key
            ).order_by('username').values('username', 'email', 'generatedcertificate__verify_uuid', 'generatedcertificate__mode')
        
        for user in enrolled_students:
            run = ''
            if 'edxloginuser__run' in user and user['edxloginuser__run'] != None:
                run = user['edxloginuser__run']
            students.append([
                user['username'],                
                run,
                user['email'],
                user['generatedcertificate__mode'],
                '{}{}'.format(base_url, reverse('certificates:render_cert_by_uuid', kwargs={'certificate_uuid':user['generatedcertificate__verify_uuid']}))])
        return students
    
    def validate_data(self, user, course_id):
        """
        Validates the course_id and the user permissions.
        """
        error = {}
        if course_id == "":
            logger.error("EolReportCertificate - Empty course, user: {}".format(user.id))
            error['empty_course'] = True
        else:
            if not self.validate_course(course_id):
                logger.error("EolReportCertificate - Course doesn't exists, user: {}, course_id: {}".format(user.id, course_id))
                error['error_curso'] = True
            else:
                if not self.user_have_permission(user, course_id):
                    logger.error("EolReportCertificate - User doesn't have permission in the course, course: {}, user: {}".format(course_id, user))
                    error['user_permission'] = True
        return error
    
    def validate_course(self, course_id):
        """
        Verify if course_id exists.
        """
        try:
            aux = CourseKey.from_string(course_id)
            return CourseOverview.objects.filter(id=aux).exists()
        except InvalidKeyError:
            return False

    def user_have_permission(self, user, course_id):
        """
        Verify if user is instructor, staff_course, data researcher or superuser.
        """
        course_key = CourseKey.from_string(course_id)
        return self.is_instructor_or_staff(user, course_key) or user.is_staff

    def is_instructor_or_staff(self, user, course_key):
        """
        Verify if the user is instructor, staff course or data researcher.
        """
        try:
            course = get_course_with_access(user, "load", course_key)
            data_researcher_access = user.has_perm(permissions.CAN_RESEARCH, course_key)
            return bool(has_access(user, 'instructor', course)) or bool(has_access(user, 'staff', course)) or data_researcher_access
        except Exception as e:
            logger.error('EolReportCertificate - Error in is_instructor_or_staff({}, {}), Exception {}'.format(user, str(course_key), str(e)))
            return False
