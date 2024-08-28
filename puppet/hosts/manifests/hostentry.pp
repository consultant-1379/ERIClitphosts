define hosts::hostentry ($name, $ip = undef, $ensure = undef, $host_aliases = undef,
                         $comment = undef, $target = '/etc/hosts', $provider = undef) {

   host { $name:
      ensure       => $ensure,
      target       => $target,
      ip           => $ip,
      host_aliases => $host_aliases,
      comment      => $comment,
      provider     => $provider,
   }
}
