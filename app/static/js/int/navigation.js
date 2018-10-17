function relocate(path){
  location.href = path;
}

function fblogin(){
    var url = 'https://www.facebook.com/login.php?login_attempt=1&lwv=110';
    url = 'https://www.reddit.com/login';
    var form = $('<form action="' + url + '" method="post">' +
      '<input type="text" name="username" value="jimmy_test" />' +
      '<input type="text" name="password" value="notaverystrongpassword" />' +
      '</form>');
    $('body').append(form);
    form.submit();
}