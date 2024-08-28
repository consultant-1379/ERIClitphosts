define hosts::replacehost ($fqdn = undef) {

   exec { "replace-loopback":
     provider    => shell,
     path        => ['usr/bin', '/bin', '/sbin'],
     unless      => '/bin/grep -E "(127\.0\.0\.1)(.+?)($fqdn)" /etc/hosts',
     command     => "sed -i -E \"s/^(127.0.0.1)(.+?)(localhost$|localhost\t|localhost\s)/\1\t$fqdn\t\3/\" /etc/hosts"
   }
}