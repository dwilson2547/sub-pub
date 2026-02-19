"""Message publishing and consumption step definitions"""

import json
import time
import subprocess
import sys
from pathlib import Path
from behave import when, then


# Message publishing steps

@when('I publish message "{message}" to source topic "{topic}"')
@when('I publish message "{message}" to topic "{topic}"')
def step_publish_message_to_topic(context, message, topic):
    """Publish a message to a topic"""
    kafka_helper = context.helpers.get('kafka')
    if kafka_helper:
        kafka_helper.publish_message(topic, message)
        if not hasattr(context, 'published_messages'):
            context.published_messages = []
        context.published_messages.append({'topic': topic, 'message': message})


@when('I publish message "{message}" with header "{header_key}" = "{header_value}" to topic "{topic}"')
def step_publish_message_with_header(context, message, header_key, header_value, topic):
    """Publish a message with headers to a topic"""
    kafka_helper = context.helpers.get('kafka')
    if kafka_helper:
        headers = {header_key: header_value}
        kafka_helper.publish_message(topic, message, headers=headers)
        if not hasattr(context, 'published_messages'):
            context.published_messages = []
        context.published_messages.append({
            'topic': topic,
            'message': message,
            'headers': headers
        })


@when('I publish JSON message {json_data} to topic "{topic}"')
def step_publish_json_message(context, json_data, topic):
    """Publish a JSON message to a topic"""
    kafka_helper = context.helpers.get('kafka')
    if kafka_helper:
        data = json.loads(json_data)
        kafka_helper.publish_message(topic, data)
        if not hasattr(context, 'published_messages'):
            context.published_messages = []
        context.published_messages.append({'topic': topic, 'message': data})


@when('I publish message "{message}" to Kafka topic "{topic}"')
def step_publish_message_to_kafka_topic(context, message, topic):
    """Publish a message to a Kafka topic explicitly"""
    kafka_helper = context.helpers.get('kafka')
    if kafka_helper:
        kafka_helper.publish_message(topic, message)
        if not hasattr(context, 'published_messages'):
            context.published_messages = []
        context.published_messages.append({'topic': topic, 'message': message, 'system': 'kafka'})


@when('I publish message "{message}" to Pulsar topic "{topic}"')
def step_publish_message_to_pulsar_topic(context, message, topic):
    """Publish a message to a Pulsar topic explicitly"""
    pulsar_helper = context.helpers.get('pulsar')
    if pulsar_helper:
        pulsar_helper.publish_message(topic, message)
        if not hasattr(context, 'published_messages'):
            context.published_messages = []
        context.published_messages.append({'topic': topic, 'message': message, 'system': 'pulsar'})


@when('I publish message "{message}" with property "{prop_key}" = "{prop_value}" to topic "{topic}"')
def step_publish_message_with_property(context, message, prop_key, prop_value, topic):
    """Publish a message with properties to a Pulsar topic"""
    pulsar_helper = context.helpers.get('pulsar')
    if pulsar_helper:
        properties = {prop_key: prop_value}
        pulsar_helper.publish_message(topic, message, properties=properties)
        if not hasattr(context, 'published_messages'):
            context.published_messages = []
        context.published_messages.append({
            'topic': topic,
            'message': message,
            'properties': properties
        })


@when('I publish {count:d} messages with alternating destinations to topic "{topic}"')
def step_publish_messages_alternating(context, count, topic):
    """Publish multiple messages with alternating destination headers"""
    kafka_helper = context.helpers.get('kafka')
    if kafka_helper:
        for i in range(count):
            dest = 'dest-a' if i % 2 == 0 else 'dest-b'
            headers = {'destination_topic': dest}
            kafka_helper.publish_message(topic, f'message-{i}', headers=headers)
        time.sleep(1)  # Give time for messages to be published


@when('I publish {count:d} messages to topic "{topic}"')
def step_publish_multiple_messages(context, count, topic):
    """Publish multiple messages to a topic"""
    kafka_helper = context.helpers.get('kafka')
    if kafka_helper:
        for i in range(count):
            kafka_helper.publish_message(topic, f'message-{i}')
        time.sleep(1)  # Give time for messages to be published


@when('I publish messages in order "{msg1}", "{msg2}", "{msg3}" to topic "{topic}"')
def step_publish_ordered_messages(context, msg1, msg2, msg3, topic):
    """Publish messages in a specific order"""
    kafka_helper = context.helpers.get('kafka')
    if kafka_helper:
        for msg in [msg1, msg2, msg3]:
            kafka_helper.publish_message(topic, msg)
            time.sleep(0.1)  # Small delay to ensure order
        time.sleep(1)


@when('I publish message "{message}" to Iggy stream "{stream}"')
def step_publish_message_to_iggy(context, message, stream):
    """Publish a message to an Iggy stream"""
    # Placeholder for Iggy publishing
    # This would require Iggy client library implementation
    pass


@when('I publish message "{message}" to Google Pub/Sub topic "{topic}"')
def step_publish_message_to_google_pubsub(context, message, topic):
    """Publish a message to a Google Pub/Sub topic"""
    # Placeholder for Google Pub/Sub publishing
    # This would require Google Pub/Sub client library implementation
    pass


# Sub-pub process steps

@when('I start sub-pub with the funnel config')
@when('I start sub-pub with the fan config')
@when('I start sub-pub with the one-to-one config')
def step_start_subpub_with_config(context):
    """Start sub-pub process with the current config"""
    assert context.current_config, "No config file specified"
    
    # Get project root
    project_root = Path(__file__).parent.parent.parent
    
    # Start sub-pub process
    process = subprocess.Popen(
        [sys.executable, '-m', 'sub_pub.main', '-c', context.current_config, '-l', 'INFO'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(project_root)
    )
    
    context.current_process = process
    context.sub_pub_processes.append(process)
    
    # Give it a moment to start
    time.sleep(2)


@when('I wait for {seconds:d} seconds')
def step_wait_for_seconds(context, seconds):
    """Wait for specified seconds"""
    time.sleep(seconds)


# Message validation steps

@then('destination topic "{topic}" should receive {count:d} messages')
@then('destination topic "{topic}" should receive {count:d} message')
def step_verify_message_count(context, topic, count):
    """Verify that a destination topic received the expected number of messages"""
    kafka_helper = context.helpers.get('kafka')
    assert kafka_helper, "Kafka helper not initialized"
    
    # Consume messages from destination topic
    messages = kafka_helper.consume_messages([topic], count=count, timeout=15)
    
    # Store consumed messages for further validation
    context.consumed_messages = messages
    
    assert len(messages) == count, f"Expected {count} messages, but got {len(messages)}"


@then('Kafka topic "{topic}" should receive {count:d} messages')
@then('Kafka topic "{topic}" should receive {count:d} message')
def step_verify_kafka_message_count(context, topic, count):
    """Verify that a Kafka topic received the expected number of messages"""
    kafka_helper = context.helpers.get('kafka')
    assert kafka_helper, "Kafka helper not initialized"
    
    messages = kafka_helper.consume_messages([topic], count=count, timeout=15)
    context.consumed_messages = messages
    
    assert len(messages) == count, f"Expected {count} messages in Kafka topic, but got {len(messages)}"


@then('Pulsar topic "{topic}" should receive {count:d} messages')
@then('Pulsar topic "{topic}" should receive {count:d} message')
def step_verify_pulsar_message_count(context, topic, count):
    """Verify that a Pulsar topic received the expected number of messages"""
    pulsar_helper = context.helpers.get('pulsar')
    assert pulsar_helper, "Pulsar helper not initialized"
    
    messages = pulsar_helper.consume_messages([topic], subscription='test-consumer', count=count, timeout=15)
    context.consumed_messages = messages
    
    assert len(messages) == count, f"Expected {count} messages in Pulsar topic, but got {len(messages)}"


@then('the message should contain "{expected_content}"')
@then('the messages should contain "{expected_content}"')
def step_verify_message_contains(context, expected_content):
    """Verify that consumed messages contain expected content"""
    assert context.consumed_messages, "No messages consumed"
    
    found = False
    for msg in context.consumed_messages:
        content = msg.get('value') or msg.get('data')
        if expected_content in str(content):
            found = True
            break
    
    assert found, f"Expected content '{expected_content}' not found in messages"


@then('one message should have header "{header_key}" = "{header_value}"')
def step_verify_message_has_header(context, header_key, header_value):
    """Verify that at least one message has the expected header"""
    assert context.consumed_messages, "No messages consumed"
    
    found = False
    for msg in context.consumed_messages:
        headers = msg.get('headers', {})
        if headers.get(header_key) == header_value:
            found = True
            break
    
    assert found, f"Expected header '{header_key}={header_value}' not found in any message"


@then('destination topic "{topic}" should receive messages in order "{msg1}", "{msg2}", "{msg3}"')
def step_verify_message_order(context, topic, msg1, msg2, msg3):
    """Verify that messages are received in the expected order"""
    kafka_helper = context.helpers.get('kafka')
    assert kafka_helper, "Kafka helper not initialized"
    
    messages = kafka_helper.consume_messages([topic], count=3, timeout=15)
    
    assert len(messages) >= 3, f"Expected at least 3 messages, but got {len(messages)}"
    
    # Check order
    expected_order = [msg1, msg2, msg3]
    actual_order = [msg.get('value') for msg in messages[:3]]
    
    assert actual_order == expected_order, f"Message order mismatch. Expected {expected_order}, got {actual_order}"
