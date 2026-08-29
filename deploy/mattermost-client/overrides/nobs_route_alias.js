(function () {
    var match = window.location.pathname.match(/^\/([^/]+)\/nobs\/calendar\/?$/);
    if (match) {
        window.history.replaceState(null, '', '/' + match[1] + '/com.noping.enterprise/calendar' + window.location.search + window.location.hash);
    }
}());
