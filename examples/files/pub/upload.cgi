secure:loggedin | when {
    OK => translate "UploadForm ** secure:TokenProperty" | when {
        OK => secure:check-token | when {
            OK => upload | "/files/" | redirect,
            NG => "不正なトークン" | request /files/
        },
        NG => "フォームの項目に誤りがあります" | request /files/
    },
    NG => redirect /security/login.html
}

