Feature: One-to-One Mode End-to-End Testing
  As a sub-pub user
  I want to map topics one-to-one between systems
  So that I can migrate or replicate data efficiently

  @kafka
  Scenario: One-to-one mapping between Kafka topics
    Given a Kafka container is running
    And a one-to-one config with 3 topic mappings
    When I publish message "order-123" to topic "orders"
    And I publish message "payment-456" to topic "payments"
    And I publish message "inventory-789" to topic "inventory"
    And I start sub-pub with the one-to-one config
    And I wait for 5 seconds
    Then destination topic "orders-processed" should receive 1 message
    And the message should contain "order-123"
    And destination topic "payments-processed" should receive 1 message
    And the message should contain "payment-456"
    And destination topic "inventory-processed" should receive 1 message
    And the message should contain "inventory-789"

  @pulsar
  Scenario: One-to-one mapping in Pulsar
    Given a Pulsar container is running
    And a one-to-one config with 2 Pulsar topic mappings
    When I publish message "pulsar-data-1" to topic "persistent://public/default/input1"
    And I publish message "pulsar-data-2" to topic "persistent://public/default/input2"
    And I start sub-pub with the one-to-one config
    And I wait for 5 seconds
    Then Pulsar topic "persistent://public/default/output1" should receive 1 message
    And Pulsar topic "persistent://public/default/output2" should receive 1 message

  @kafka @pulsar
  Scenario: Cross-system one-to-one from Kafka to Pulsar
    Given a Kafka container is running
    And a Pulsar container is running
    And a one-to-one config with Kafka source and Pulsar destination
    When I publish message "migrate-message-1" to Kafka topic "kafka-orders"
    And I publish message "migrate-message-2" to Kafka topic "kafka-payments"
    And I start sub-pub with the one-to-one config
    And I wait for 5 seconds
    Then Pulsar topic "persistent://public/default/pulsar-orders" should receive 1 message
    And Pulsar topic "persistent://public/default/pulsar-payments" should receive 1 message

  @kafka
  Scenario: One-to-one with message ordering preserved
    Given a Kafka container is running
    And a one-to-one config with 1 topic mapping
    When I publish messages in order "msg1", "msg2", "msg3" to topic "ordered-input"
    And I start sub-pub with the one-to-one config
    And I wait for 5 seconds
    Then destination topic "ordered-output" should receive messages in order "msg1", "msg2", "msg3"

  @kafka
  Scenario: One-to-one mode handles high throughput
    Given a Kafka container is running
    And a one-to-one config with 2 topic mappings
    When I publish 100 messages to topic "high-volume-1"
    And I publish 100 messages to topic "high-volume-2"
    And I start sub-pub with the one-to-one config
    And I wait for 15 seconds
    Then destination topic "high-volume-1-out" should receive 100 messages
    And destination topic "high-volume-2-out" should receive 100 messages
