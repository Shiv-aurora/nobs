(function () {
    var match = window.location.pathname.match(/^\/([^/]+)\/nobs\/(calendar|workrooms)\/?$/);
    if (match) {
        window.history.replaceState(null, '', '/' + match[1] + '/com.noping.enterprise/' + match[2] + window.location.search + window.location.hash);
    }
}());
