# Copyright (c) Rackspace US, Inc.
# See LICENSE for details.

"""
Tests for L{udplog.kafka}.
"""
from __future__ import division, absolute_import

import simplejson
from twisted.internet import defer
from twisted.trial import unittest

from udplog import kafka
from udplog.twisted import Dispatcher

class FakeKafkaProducer(object):

    def __init__(self):
        self.produced = []


    def send_messages(self, topic, message):
        self.produced.append((topic, message))
        return True


    def stop(self):
        pass



class KafkaPublisherServiceTest(unittest.TestCase):

    def setUp(self):
        self.dispatcher = Dispatcher()
        self.producer = FakeKafkaProducer()
        kafka._make_producer = lambda _: self.producer
        config = {
            'kafka-topic': 'foo'
        }
        self.publisher = kafka.KafkaPublisher(self.dispatcher, config)


    @defer.inlineCallbacks
    def test_startService(self):
        """
        The publisher registers itself with the dispatcher.
        """
        event = {'message': 'test'}
        self.dispatcher.eventReceived(event)
        self.assertEqual(0, len(self.producer.produced))
        # When
        yield self.publisher.startService()
        # Then
        self.dispatcher.eventReceived(event)
        self.assertEqual(1, len(self.producer.produced))


    @defer.inlineCallbacks
    def test_stopService(self):
        """
        The publisher registers itself with the dispatcher.
        """
        event = {'message': 'test'}
        yield self.publisher.startService()
        self.dispatcher.eventReceived(event)
        # When
        self.publisher.stopService()
        # Then
        self.dispatcher.eventReceived(event)
        self.assertEqual(1, len(self.producer.produced))


    @defer.inlineCallbacks
    def test_sendEvent(self):
        """
        An event is pushed as a JSON string.
        """
        event = {'category': u'test',
                 'message': u'test',
                 'timestamp': 1340634165}
        yield self.publisher.startService()
        # When
        self.dispatcher.eventReceived(event)
        # Then
        output = self.producer.produced[-1]
        self.assertEqual('foo', output[0])
        eventDict = simplejson.loads(output[1])
        self.assertEqual(event, eventDict)


    @defer.inlineCallbacks
    def test_sendEventUnserializable(self):
        """
        An event that cannot be serialized is dropped and an error logged.
        """
        class Object(object):
            pass

        event = {'category': u'test',
                 'message': Object(),
                 'timestamp': 1340634165}
        yield self.publisher.startService()
        # When
        self.dispatcher.eventReceived(event)
        # Then
        self.assertEqual(0, len(self.producer.produced))
        self.assertEqual(1, len(self.flushLoggedErrors(TypeError)))
