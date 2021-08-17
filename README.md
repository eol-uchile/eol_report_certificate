# Eol Report Certificate

![https://github.com/eol-uchile/eol_report_certificate/actions](https://github.com/eol-uchile/eol_report_certificate/workflows/Python%20application/badge.svg)

Export CSV of Certificates Issued.

# Install App

    docker-compose exec lms pip install -e /openedx/requirements/eol_report_certificate
    docker-compose exec lms_worker pip install -e /openedx/requirements/eol_report_certificate

# Install Theme

To enable export certificate issued button in your theme add next file and/or lines code:

- _../themes/your_theme/lms/templates/instructor/instructor_dashboard_2/data_download.html_

    **add the script and css**

        <script type="text/javascript" src="${static.url('eolreportcertificate/js/eolreportcertificate.js')}"></script>
        <link rel="stylesheet" type="text/css" href="${static.url('eolreportcertificate/css/eolreportcertificate.css')}"/>

    **and add html button**

        <div class="issued_certificates">
            ...
            <p>
                ...
                %if 'has_eolreportcertificate' in section_data and section_data['has_eolreportcertificate']:
                    <input type="button" name="issued-certificates-eol" onclick="generate_eolreportcertificate(this)" value="${_("(Nuevo) Descargar Reporte de Certificados")}" data-endpoint="${ section_data['eolreportcertificate_url'] }">
                %endif
            </p>
            %if 'has_eolreportcertificate' in section_data and section_data['has_eolreportcertificate']:
                <div class="eolreportcertificate-success-msg" id="eolreportcertificate-success-msg"></div>
                <div class="eolreportcertificate-warning-msg" id="eolreportcertificate-warning-msg"></div>
                <div class="eolreportcertificate-error-msg" id="eolreportcertificate-error-msg"></div>
            %endif
            ...
        </div>

- In your edx-platform add the following code in the function '_section_data_download' in _edx-platform/lms/djangoapps/instructor/views/instructor_dashboard.py_

        try:
            from eolreportcertificate import views
            import urllib
            section_data['has_eolreportcertificate'] = True
            section_data['eolreportcertificate_url'] = '{}?{}'.format(reverse('eolreportcertificate-export:data'), urllib.parse.urlencode({'course': str(course_key)}))
        except ImportError:
            section_data['has_eolreportcertificate'] = False

## TESTS
**Prepare tests:**

    > cd .github/
    > docker-compose run lms /openedx/requirements/eol_report_certificate/.github/test.sh

## Notes

- Check in edx-platform Lilac version if AlreadyRunningError work