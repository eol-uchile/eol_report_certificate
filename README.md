# Eol Report Certificate

![Coverage Status](/coverage-badge.svg)


![https://github.com/eol-uchile/eol_report_certificate/actions](https://github.com/eol-uchile/eol_report_certificate/workflows/Python%20application/badge.svg)

Export CSV of Certificates Issued.

# Install App

    docker-compose exec lms pip install -e /openedx/requirements/eol_report_certificate
    docker-compose exec lms_worker pip install -e /openedx/requirements/eol_report_certificate

# Install Theme

To enable the export issued certificates button, add the following code to your theme. This includes a conditional check to ensure the template only renders if the app is installed.

- _../themes/your_theme/lms/templates/instructor/instructor_dashboard_2/data_download.html_

    **add eol_report_certificate template to the data_download template**

        <%
        eolreportcertificate_url = None
        eolreportcertificate_traceback = None
        try:
          eolreportcertificate_url = reverse('eolreportcertificate-export:data')
        except Exception:
          if settings.DEBUG:
            eolreportcertificate_traceback = traceback.format_exc()
        %>  
        %if eolreportcertificate_traceback:
          <div class="eolreportcertificate_traceback">
          <pre>${eolreportcertificate_traceback}</pre>
          </div>
        %elif eolreportcertificate_url:
          <%include file="eol_report_certificate.html"/>
        %endif

### Adding new translations:

To extract and update any new translatable text, run the update command below. After manually filling in the new translations, run the compile command to update the .mo translation files.

### Commands

**Update**

    docker run -it --rm -w /code -v $(pwd):/code python:3.8 bash
    pip install -r requirements-i18n.in
    make update_translations

**Compile**

    docker run -it --rm -w /code -v $(pwd):/code python:3.8 bash
    pip install -r requirements-i18n.in
    make compile_translations

## TESTS
**Prepare tests:**

- Install **act** following the instructions in [https://nektosact.com/installation/index.html](https://nektosact.com/installation/index.html)

**Run tests:**
- In a terminal at the root of the project
    ```
    act -W .github/workflows/pythonapp.yml
    ```
## Notes

- Check in edx-platform Lilac version if AlreadyRunningError work
