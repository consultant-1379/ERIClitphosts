
class task_node1__hosts_3a_3ahostentry__ms1(){
    hosts::hostentry { "ms1":
        comment => "Created by LITP. Please do not edit",
        ensure => "present",
        ip => "10.4.23.50",
        name => "ms1"
    }
}

class task_node1__hosts_3a_3ahostentry__node1(){
    hosts::hostentry { "node1":
        comment => "Created by LITP. Please do not edit",
        ensure => "present",
        ip => "10.4.23.51",
        name => "node1"
    }
}

class task_node1__hosts_3a_3ahostentry__node2(){
    hosts::hostentry { "node2":
        comment => "Created by LITP. Please do not edit",
        ensure => "present",
        ip => "10.4.23.52",
        name => "node2"
    }
}

class task_node1__hosts_3a_3areplacehost__node1(){
    hosts::replacehost { "node1":
        fqdn => ""
    }
}


node "node1" {

    class {'litp::mn_node':
        ms_hostname => "ms1",
        cluster_type => "NON-CMW"
        }


    class {'task_node1__hosts_3a_3ahostentry__ms1':
    }


    class {'task_node1__hosts_3a_3ahostentry__node1':
    }


    class {'task_node1__hosts_3a_3ahostentry__node2':
    }


    class {'task_node1__hosts_3a_3areplacehost__node1':
    }


}