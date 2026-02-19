Feature: Cross-System Integration Testing
  As a sub-pub user
  I want to route messages between different message systems
  So that I can integrate heterogeneous infrastructure

  @kafka @pulsar
  Scenario: Kafka to Pulsar message routing
    Given a Kafka container is running
    And a Pulsar container is running
    And a one-to-one config routing Kafka to Pulsar
    When I publish message "kafka-to-pulsar-test" to Kafka topic "kafka-src"
    And I start sub-pub with the one-to-one config
    And I wait for 15 seconds
    Then Pulsar topic "persistent://public/default/pulsar-dst" should receive 1 message
    And the message should contain "kafka-to-pulsar-test"

  @kafka @pulsar
  Scenario: Pulsar to Kafka message routing
    Given a Kafka container is running
    And a Pulsar container is running
    And a one-to-one config routing Pulsar to Kafka
    When I publish message "pulsar-to-kafka-test" to Pulsar topic "persistent://public/default/pulsar-src"
    And I start sub-pub with the one-to-one config
    And I wait for 15 seconds
    Then Kafka topic "kafka-dst" should receive 1 message
    And the message should contain "pulsar-to-kafka-test"

  @kafka @pulsar
  Scenario: Bi-directional message flow between Kafka and Pulsar
    Given a Kafka container is running
    And a Pulsar container is running
    And a funnel config with Kafka and Pulsar sources to Kafka destination
    When I publish message "from-kafka" to Kafka topic "kafka-input"
    And I publish message "from-pulsar" to Pulsar topic "persistent://public/default/pulsar-input"
    And I start sub-pub with the funnel config
    And I wait for 15 seconds
    Then Kafka topic "mixed-output" should receive 2 messages
    And the messages should contain "from-kafka"
    And the messages should contain "from-pulsar"

  @iggy @kafka
  Scenario: Iggy to Kafka message routing
    Given an Iggy container is running
    And a Kafka container is running
    And a one-to-one config routing Iggy to Kafka
    When I publish message "iggy-message" to Iggy stream "test-stream"
    And I start sub-pub with the one-to-one config
    And I wait for 15 seconds
    Then Kafka topic "kafka-from-iggy" should receive 1 message

  @google_pubsub @kafka
  Scenario: Google Pub/Sub to Kafka message routing
    Given a Google Pub/Sub emulator is running
    And a Kafka container is running
    And a one-to-one config routing Google Pub/Sub to Kafka
    When I publish message "pubsub-message" to Google Pub/Sub topic "test-topic"
    And I start sub-pub with the one-to-one config
    And I wait for 15 seconds
    Then Kafka topic "kafka-from-pubsub" should receive 1 message
