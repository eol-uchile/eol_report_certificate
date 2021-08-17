function generate_eolreportcertificate(input){
    cleanEolReportCertificate()
    var success_div = document.getElementById('eolreportcertificate-success-msg');
    var error_div = document.getElementById('eolreportcertificate-error-msg');
    var warning_div = document.getElementById('eolreportcertificate-warning-msg');
    var post_url = input.dataset.endpoint;
    $.ajax({
        dataType: 'json',
        type: 'GET',
        url: post_url,
        success: function(data) {
            if (data["status"] == 'Generating'){
              success_div.textContent = "El reporte se está generando, en un momento estará disponible para descargar.";
              success_div.style.display = "block";
            }
            if (data["status"] == 'AlreadyRunningError'){
              warning_div.textContent = 'El reporte ya se está generando, por favor espere.'
              warning_div.style.display = "block";
            }
            if (data["status"] == 'Error'){
                return EolReportCertificateDataError(data);
            }
        },
        error: function() {
            error_div.textContent = 'Error al exportar, actualice la página e intentelo nuevamente, si el error persiste contáctese con la mesa de ayuda(eol-ayuda@uchile.cl).'
            error_div.style.display = "block";
        }
    })
}
function cleanEolReportCertificate(){
    document.getElementById('eolreportcertificate-success-msg').style.display = "none";
    document.getElementById('eolreportcertificate-success-msg').textContent = "";
    document.getElementById('eolreportcertificate-error-msg').style.display = "none";
    document.getElementById('eolreportcertificate-error-msg').textContent = "";
    document.getElementById('eolreportcertificate-warning-msg').style.display = "none";
    document.getElementById('eolreportcertificate-warning-msg').textContent = "";
}
function EolReportCertificateDataError(data){
    var error_msg = document.getElementById('eolreportcertificate-error-msg');
    if (data['user_permission']){
      error_msg.textContent = 'Usuario no tiene permisos para realizar esta acción.';
    }
    else{
      error_msg.textContent = 'Error al exportar, actualice la página e intentelo nuevamente, si el error persiste contáctese con la mesa de ayuda(eol-ayuda@uchile.cl).'
    }
    
    error_msg.style.display = "block";
}