
class task_node2__hosts_3a_3ahostentry__cluster2__node2__master2(){
    hosts::hostentry { "cluster2_node2_master2":
        comment => "Created by LITP. Please do not edit",
        ensure => "present",
        ip => "33.33.33.3",
        name => "master2"
    }
}

class task_node2__hosts_3a_3ahostentry__ms1(){
    hosts::hostentry { "ms1":
        comment => "Created by LITP. Please do not edit",
        ensure => "present",
        ip => "10.4.23.50",
        name => "ms1"
    }
}

class task_node2__hosts_3a_3ahostentry__node1(){
    hosts::hostentry { "node1":
        comment => "Created by LITP. Please do not edit",
        ensure => "present",
        ip => "10.4.23.51",
        name => "node1"
    }
}

class task_node2__hosts_3a_3ahostentry__node2(){
    hosts::hostentry { "node2":
        comment => "Created by LITP. Please do not edit",
        ensure => "present",
        ip => "10.4.23.52",
        name => "node2"
    }
}


node "node2" {

    class {'litp::mn_node':
        ms_hostname => "ms1",
        cluster_type => "NON-CMW"
        }


    class {'task_node2__hosts_3a_3ahostentry__cluster2__node2__master2':
    }


    class {'task_node2__hosts_3a_3ahostentry__ms1':
    }


    class {'task_node2__hosts_3a_3ahostentry__node1':
    }


    class {'task_node2__hosts_3a_3ahostentry__node2':
    }


}