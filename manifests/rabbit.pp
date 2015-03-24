class { '::rabbitmq':
  service_manage    => true,
  port              => '5672',
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