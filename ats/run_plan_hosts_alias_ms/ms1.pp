
class task_ms1__hosts_3a_3ahostentry____ms1__master1(){
    hosts::hostentry { "_ms1_master1":
        comment => "Created by LITP. Please do not edit",
        ensure => "present",
host_aliases => [
        "master2"
        ]
,
        ip => "11.11.11.1",
        name => "master1"
    }
}

class task_ms1__hosts_3a_3ahostentry__ms1(){
    hosts::hostentry { "ms1":
        comment => "Created by LITP. Please do not edit",
        ensure => "present",
        ip => "10.4.23.50",
        name => "ms1"
    }
}

class task_ms1__hosts_3a_3ahostentry__node1(){
    hosts::hostentry { "node1":
        comment => "Created by LITP. Please do not edit",
        ensure => "present",
        ip => "10.4.23.51",
        name => "node1"
    }
}

class task_ms1__hosts_3a_3ahostentry__node2(){
    hosts::hostentry { "node2":
        comment => "Created by LITP. Please do not edit",
        ensure => "present",
        ip => "10.4.23.52",
        name => "node2"
    }
}

class task_ms1__hosts_3a_3areplacehost__ms1(){
    hosts::replacehost { "ms1":
        fqdn => "ms1"
    }
}


node "ms1" {

    class {'litp::ms_node':}


    class {'task_ms1__hosts_3a_3ahostentry____ms1__master1':
        require => [Class["task_ms1__hosts_3a_3ahostentry__ms1"],Class["task_ms1__hosts_3a_3areplacehost__ms1"]]
    }


    class {'task_ms1__hosts_3a_3ahostentry__ms1':
    }


    class {'task_ms1__hosts_3a_3ahostentry__node1':
    }


    class {'task_ms1__hosts_3a_3ahostentry__node2':
    }


    class {'task_ms1__hosts_3a_3areplacehost__ms1':
    }


}