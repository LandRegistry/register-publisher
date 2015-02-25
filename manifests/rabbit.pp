class { '::rabbitmq':
  service_manage    => true,
  port              => '5672',
}