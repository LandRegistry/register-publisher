class { '::rabbitmq':
  service_manage    => true,
  port              => '5672',
}

rabbitmq_user { 'mqpublisher':
  admin    => true,
  password => 'mqpublisherpassword',
}
