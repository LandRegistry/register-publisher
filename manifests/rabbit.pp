class { '::rabbitmq':
  service_manage    => true,
  port              => '5672',
  package_source    => 'https://github.com/rabbitmq/rabbitmq-server/releases/download/rabbitmq_v3_4_4/rabbitmq-server-3.4.4-1.noarch.rpm'
}

rabbitmq_user { 'mqpublisher':
admin    => true,
password => 'mqpublisherpassword',
}

rabbitmq_user_permissions { 'mqpublisher@/':
 configure_permission => '.*',
 read_permission      => '.*',
 write_permission     => '.*',
}
