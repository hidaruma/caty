translate secure:LoginForm | when {
    OK => secure:login ,
    NG => "ユーザ名かパスワードが間違っています" | print /secure/login.html,
}

