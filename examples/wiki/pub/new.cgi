translate NewWiki | when {
    OK => pv filename | text:regmatch "[A-Z][a-z0-9]" | when {
        match => {"title": pv src, "body": ""} | print include@this:/edit.html,
        fail => redirect /
    },
    NG => redirect /
}
