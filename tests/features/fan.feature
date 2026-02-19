Feature: Fan Mode End-to-End Testing
  As a sub-pub user
  I want to route messages from one source to multiple destinations
  So that I can distribute data based on message content

  @kafka
  Scenario: Fan messages based on header routing
    Given a Kafka container is running
    And a fan config with header-based routing using key "destination_topic"
    When I publish message "order-data" with header "destination_topic" = "orders" to topic "fan-source"
    And I publish message "payment-data" with header "destination_topic" = "payments" to topic "fan-source"
    And I start sub-pub with the fan config
    And I wait for 15 seconds
    Then destination topic "orders" should receive 1 message
    And the message should contain "order-data"
    And destination topic "payments" should receive 1 message
    And the message should contain "payment-data"

  @kafka
  Scenario: Fan messages based on payload routing
    Given a Kafka container is running
    And a fan config with payload-based routing using key "routing_key"
    When I publish JSON message {"routing_key": "metrics", "data": "cpu-usage"} to topic "fan-source"
    And I publish JSON message {"routing_key": "logs", "data": "error-log"} to topic "fan-source"
    And I start sub-pub with the fan config
    And I wait for 15 seconds
    Then destination topic "metrics" should receive 1 message
    And destination topic "logs" should receive 1 message

  @pulsar
  Scenario: Fan messages in Pulsar
    Given a Pulsar container is running
    And a fan config with Pulsar header-based routing using key "destination"
    When I publish message "event1" with property "destination" = "stream1" to topic "persistent://public/default/fan-input"
    And I publish message "event2" with property "destination" = "stream2" to topic "persistent://public/default/fan-input"
    And I start sub-pub with the fan config
    And I wait for 15 seconds
    Then Pulsar topic "persistent://public/default/stream1" should receive 1 message
    And Pulsar topic "persistent://public/default/stream2" should receive 1 message

  @kafka
  Scenario: Fan mode with high message volume
    Given a Kafka container is running
    And a fan config with header-based routing using key "destination_topic"
    When I publish 50 messages with alternating destinations to topic "fan-source"
    And I start sub-pub with the fan config
    And I wait for 10 seconds
    Then destination topic "dest-a" should receive 25 messages
    And destination topic "dest-b" should receive 25 messages
