Feature: Funnel Mode End-to-End Testing
  As a sub-pub user
  I want to aggregate messages from multiple sources into one destination
  So that I can centralize data from distributed systems

  @kafka
  Scenario: Funnel messages from two Kafka sources to one Kafka destination
    Given a Kafka container is running
    And a funnel config with 2 Kafka sources and 1 Kafka destination
    When I publish message "message1" to source topic "source-topic-1"
    And I publish message "message2" to source topic "source-topic-2"
    And I start sub-pub with the funnel config
    And I wait for 5 seconds
    Then destination topic "funnel-destination" should receive 2 messages
    And the messages should contain "message1"
    And the messages should contain "message2"

  @kafka
  Scenario: Funnel mode with message headers preserved
    Given a Kafka container is running
    And a funnel config with 2 Kafka sources and 1 Kafka destination
    When I publish message "test-data" with header "source" = "system1" to topic "source-topic-1"
    And I publish message "test-data" with header "source" = "system2" to topic "source-topic-2"
    And I start sub-pub with the funnel config
    And I wait for 5 seconds
    Then destination topic "funnel-destination" should receive 2 messages
    And one message should have header "source" = "system1"
    And one message should have header "source" = "system2"

  @pulsar
  Scenario: Funnel messages from Pulsar topics
    Given a Pulsar container is running
    And a funnel config with 2 Pulsar sources and 1 Pulsar destination
    When I publish message "pulsar-msg1" to source topic "persistent://public/default/source1"
    And I publish message "pulsar-msg2" to source topic "persistent://public/default/source2"
    And I start sub-pub with the funnel config
    And I wait for 5 seconds
    Then destination topic "persistent://public/default/funnel-dest" should receive 2 messages

  @kafka @pulsar
  Scenario: Cross-system funnel from Kafka to Pulsar
    Given a Kafka container is running
    And a Pulsar container is running
    And a funnel config with 1 Kafka source and 1 Pulsar destination
    When I publish message "cross-system-message" to Kafka topic "kafka-source"
    And I start sub-pub with the funnel config
    And I wait for 5 seconds
    Then Pulsar topic "persistent://public/default/kafka-to-pulsar" should receive 1 message
    And the message should contain "cross-system-message"
