document.getElementById("select-scan").addEventListener("change", change_scan);


function change_scan() {
    // TODO Only change scan_number param if exists so as to not break other configs
    let scan_number = document.getElementById("select-scan").value;
    window.location.replace(location.protocol + '//' + location.host + location.pathname + "?scan_number=" + scan_number)
}