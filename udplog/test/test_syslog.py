# -*- coding: utf-8 -*-
# Copyright (c) Ralph Meijer.
# See LICENSE for details.

"""
Tests for L{udplog.syslog}.
"""

from __future__ import division, absolute_import

from dateutil import tz
import datetime

from twisted.trial.unittest import TestCase

from udplog import syslog

class ParsePriorityTests(TestCase):
    """
    Tests for L{syslog.parsePriority}.
    """

    def test_priority13(self):
        """
        Priority of 13 means facility user, severity notice.
        """
        self.assertEqual(('user', 'notice'), syslog.parsePriority(13))


    def test_priority29(self):
        """
        Priority of 29 means facility daemon, severity notice.
        """
        self.assertEqual(('daemon', 'notice'), syslog.parsePriority(29))


    def test_priority191(self):
        """
        191 is the highest valid priority value.
        """
        self.assertEqual(('local7', 'debug'), syslog.parsePriority(191))


    def test_priority192(self):
        """
        Priority cannot exceed 191.
        """
        self.assertRaises(IndexError, syslog.parsePriority, 192)



class ParseSyslogTests(TestCase):
    """
    Tests for L{syslog.parseSyslog}.
    """

    def setUp(self):
        self.tz = tz.gettz('Europe/Amsterdam')


    def test_priority(self):
        """
        The priority is extracted and decoded into facility and severity.
        """
        line = b"<13>Jan 15 16:59:26 myhost test: hello"
        result = syslog.parseSyslog(line, self.tz)
        self.assertEqual('user', result['facility'])
        self.assertEqual('notice', result['severity'])


    def test_priorityInvalid(self):
        """
        The C{'facility'} and C{'severity'} are omitted for invalid priorities.
        """
        line = b"<192>Jan 15 16:59:26 myhost test: hello"
        result = syslog.parseSyslog(line, self.tz)
        self.assertNotIn('facility', result)
        self.assertNotIn('severity', result)


    def test_message(self):
        """
        The message is extracted from the log line.
        """
        line = b"<13>Jan 15 16:59:26 myhost test: hello"
        result = syslog.parseSyslog(line, self.tz)
        self.assertEqual(u'hello', result['message'])


    def test_messageBOM(self):
        """
        The message with leading BOM is decoded as UTF-8.
        """
        line = b"<13>Jan 15 16:59:26 myhost test: \xef\xbb\xbfol\xc3\xa1"
        result = syslog.parseSyslog(line, self.tz)
        self.assertEqual(u'olá', result['message'])


    def test_messageBOMAbsent(self):
        """
        The message without leading BOM is decoded as latin1.
        """
        line = b"<13>Jan 15 16:59:26 myhost test: ol\xe1"
        result = syslog.parseSyslog(line, self.tz)
        self.assertEqual(u'olá', result['message'])


    def test_timestamp(self):
        """
        Timestamp is converted to a L{datetime} in the given timezone.
        """
        line = b"<13>Jan 15 16:59:26 myhost test: hello"
        result = syslog.parseSyslog(line, self.tz)
        timestamp = datetime.datetime(2015, 1, 15, 15, 59, 26, tzinfo=tz.tzutc())
        self.assertEqual(timestamp, result['timestamp'])


    def test_timestampOtherZone(self):
        """
        Timestamp is converted to a L{datetime} in the other timezone.
        """
        line = b"<13>Jan 15 16:59:26 myhost test: hello"
        result = syslog.parseSyslog(line, tz.gettz('America/Los Angeles'))
        timestamp = datetime.datetime(2015, 1, 16, 00, 59, 26, tzinfo=tz.tzutc())
        self.assertEqual(timestamp, result['timestamp'])


    def test_timestampSingleDigitDay(self):
        """
        Single digit days without leading space are parsed correctly.
        """
        line = b"<13>Jan 5 16:59:26 myhost test: hello"
        result = syslog.parseSyslog(line, self.tz)
        timestamp = datetime.datetime(2015, 1, 5, 15, 59, 26, tzinfo=tz.tzutc())
        self.assertEqual(timestamp, result['timestamp'])


    def test_timestampSingleDigitDaySpace(self):
        """
        Single digit days with leading space are parsed correctly.
        """
        line = b"<13>Jan  5 16:59:26 myhost test: hello"
        result = syslog.parseSyslog(line, self.tz)
        timestamp = datetime.datetime(2015, 1, 5, 15, 59, 26, tzinfo=tz.tzutc())
        self.assertEqual(timestamp, result['timestamp'])


    def test_timestampSingleDigitDayZero(self):
        """
        Single digit days with leading zero are parsed correctly.
        """
        line = b"<13>Jan 05 16:59:26 myhost test: hello"
        result = syslog.parseSyslog(line, self.tz)
        timestamp = datetime.datetime(2015, 1, 5, 15, 59, 26, tzinfo=tz.tzutc())
        self.assertEqual(timestamp, result['timestamp'])


    def test_timestampInvalid(self):
        """
        Invalid dates result in no timestamp, error logged.
        """
        line = b"<13>Foo 15 16:59:26 myhost test: hello"
        result = syslog.parseSyslog(line, self.tz)
        self.assertNotIn('timestamp', result)
        self.assertEqual(1, len(self.flushLoggedErrors(ValueError)))


    def test_timestampRFC3339(self):
        """
        RFC3339/ISO8601 timestamp are parsed.
        """
        line = b"<13>2015-01-15T15:59:26.341-00 myhost test: hello"
        result = syslog.parseSyslog(line, self.tz)
        timestamp = datetime.datetime(2015, 1, 15, 15, 59, 26, 341000,
                                      tzinfo=tz.tzutc())
        self.assertEqual(timestamp, result['timestamp'])


    def test_hostname(self):
        """
        The hostname is extracted.
        """
        line = b"<13>Jan 15 16:59:26 myhost test: hello"
        result = syslog.parseSyslog(line, self.tz)
        self.assertEqual('myhost', result['hostname'])


    def test_hostnameEmpty(self):
        """
        The message is extracted from the log line.
        """
        line = b"<13>Jan 15 16:59:26  test: hello"
        result = syslog.parseSyslog(line, self.tz)
        self.assertEqual('', result['hostname'])


    def test_tag(self):
        """
        The tag is extracted.
        """
        line = b"<13>Jan 15 16:59:26 myhost test: hello"
        result = syslog.parseSyslog(line, self.tz)
        self.assertEqual('test', result['tag'])


    def test_tagFollowedByPID(self):
        """
        If a tag is followed by a PID, the PID is not included.
        """
        line = ("<29>Jan 16 15:08:58 myhost wpa_supplicant[1432]: "
                "wlan0: CTRL-EVENT-SCAN-STARTED ")
        result = syslog.parseSyslog(line, self.tz)
        self.assertEqual('wpa_supplicant', result['tag'])


    def test_pid(self):
        """
        The optional PID is extracted.
        """
        line = ("<29>Jan 16 15:08:58 myhost wpa_supplicant[1432]: "
                "wlan0: CTRL-EVENT-SCAN-STARTED ")
        result = syslog.parseSyslog(line, self.tz)
        self.assertEqual('1432', result['pid'])
        self.assertEqual('wlan0: CTRL-EVENT-SCAN-STARTED ',
                          result['message'])


    def test_invalidFormat(self):
        """
        If the log line cannot be parsed, it is returned as the message.
        """
        line = b"something"
        result = syslog.parseSyslog(line, self.tz)
        self.assertEqual(u'something', result['message'])


    def test_cee(self):
        """
        If there's a CEE structure in the message, its fields are merged in.
        """
        line = (b'<13>Jan 16 21:00:00 waar ralphm: '
                b'blah @cee: {"event": "started"}')
        result = syslog.parseSyslog(line, self.tz)
        self.assertEqual(u'blah', result['message'])
        self.assertEqual('started', result['event'])


    def test_ceeInvalid(self):
        """
        If the CEE structure is invalid, the message field includes it.
        """
        line = (b'<13>Jan 16 21:00:00 waar ralphm: '
                b'blah @cee: {"event": "started}')
        result = syslog.parseSyslog(line, self.tz)
        self.assertEqual(u'blah @cee: {"event": "started}', result['message'])
        self.assertNotIn('event', result)
        self.assertEqual(1, len(self.flushLoggedErrors(ValueError)))


    def test_ceeEmptyMessage(self):
        """
        If the message starts with the CEE marker, the message is empty.
        """
        line = (b'<13>Jan 16 21:00:00 waar ralphm: '
                b'@cee: {"event": "started"}')
        result = syslog.parseSyslog(line, self.tz)
        self.assertEqual(u'', result['message'])
        self.assertEqual('started', result['event'])



class SyslogToUDPLogEventTests(TestCase):
    """
    Tests for L{syslog.syslogToUDPLogEvent}.
    """

    def test_timestamp(self):
        """
        The event timestamp is converted to a POSIX timestamp.
        """
        eventDict = {
                'timestamp': datetime.datetime(2015, 1, 15, 15, 59, 26,
                                               tzinfo=tz.tzutc())
                }
        eventDict = syslog.syslogToUDPLogEvent(eventDict)
        self.assertEqual(1421337566, eventDict['timestamp'])


    def test_timestampSubSecond(self):
        """
        Datetimes with microseconds yield a fractional timestamp.
        """
        eventDict = {
                'timestamp': datetime.datetime(2015, 1, 15, 15, 59, 26, 341000,
                                               tzinfo=tz.tzutc())
                }
        eventDict = syslog.syslogToUDPLogEvent(eventDict)
        self.assertEqual(1421337566.341, eventDict['timestamp'])


    def test_categoryDefault(self):
        """
        If the category is not set, it is set to C{'syslog'}.
        """
        eventDict = {}
        eventDict = syslog.syslogToUDPLogEvent(eventDict)
        self.assertEqual('syslog', eventDict['category'])


    def test_categoryAlreadySet(self):
        """
        If the category is set, it is left unchanged.
        """
        eventDict = {'category': 'test'}
        eventDict = syslog.syslogToUDPLogEvent(eventDict)
        self.assertEqual('test', eventDict['category'])


    def test_tag(self):
        """
        If the syslog event has a tag, it is renamed to appname.
        """
        eventDict = {'tag': 'test'}
        eventDict = syslog.syslogToUDPLogEvent(eventDict)
        self.assertEqual('test', eventDict['appname'])
        self.assertNotIn('tag', eventDict)


    def test_severity(self):
        """
        If the syslog event has a severity, it is renamed, mapped to logLevel.
        """
        eventDict = {'severity': 'debug'}
        eventDict = syslog.syslogToUDPLogEvent(eventDict)
        self.assertEqual('DEBUG', eventDict['logLevel'])
        self.assertNotIn('severity', eventDict)


    def test_severityEmerg(self):
        """
        The syslog severity 'emerg' is mapped to 'EMERGENCY'.
        """
        eventDict = {'severity': 'emerg'}
        eventDict = syslog.syslogToUDPLogEvent(eventDict)
        self.assertEqual('EMERGENCY', eventDict['logLevel'])


    def test_severityCrit(self):
        """
        The syslog severity 'crit' is mapped to 'CRITICAL'.
        """
        eventDict = {'severity': 'crit'}
        eventDict = syslog.syslogToUDPLogEvent(eventDict)
        self.assertEqual('CRITICAL', eventDict['logLevel'])


    def test_severityErr(self):
        """
        The syslog severity 'err' is mapped to 'ERROR'.
        """
        eventDict = {'severity': 'err'}
        eventDict = syslog.syslogToUDPLogEvent(eventDict)
        self.assertEqual('ERROR', eventDict['logLevel'])
        self.assertNotIn('severity', eventDict)


    def test_severityWarn(self):
        """
        The syslog severity 'warn' is mapped to 'WARNING'.
        """
        eventDict = {'severity': 'warn'}
        eventDict = syslog.syslogToUDPLogEvent(eventDict)
        self.assertEqual('WARNING', eventDict['logLevel'])
        self.assertNotIn('severity', eventDict)


    def test_hostnames(self):
        """
        A matching hostname in the hostname mapping overrides.
        """
        eventDict = {'hostname': 'test'}
        eventDict = syslog.syslogToUDPLogEvent(
            eventDict,
            hostnames={'test': 'test.example.org'})
        self.assertEqual('test.example.org', eventDict['hostname'])


    def test_defaultHostnameNoMatch(self):
        """
        A non-matching hostname in the hostname mapping remains unchanged.
        """
        eventDict = {'hostname': 'foo'}
        eventDict = syslog.syslogToUDPLogEvent(
            eventDict,
            hostnames={'test': 'test.example.org'})
        self.assertEqual('foo', eventDict['hostname'])



class SyslogDatagramProtocolTests(TestCase):
    """
    Tests for L{syslog.SyslogDatagramProtocol}.
    """

    def test_basic(self):
        out = []
        protocol = syslog.SyslogDatagramProtocol(out.append)
        datagram = b'<13>Jan 15 16:59:26 myhost test: hello'
        protocol.datagramReceived(datagram, None)

        self.assertEqual(1, len(out))

        eventDict = out[-1]
        self.assertEqual(u'syslog', eventDict['category'])
        self.assertEqual(u'NOTICE', eventDict['logLevel'])
        self.assertGreater(eventDict['timestamp'], 0)
        self.assertEqual(u'myhost', eventDict['hostname'])
        self.assertEqual(u'hello', eventDict['message'])


    def test_hostname(self):
        """
        Hostnames are mapped.
        """
        out = []
        protocol = syslog.SyslogDatagramProtocol(
            out.append,
            hostnames={'myhost': 'myhost.example.org'})
        datagram = b'<13>Jan 15 16:59:26 myhost test: hello'
        protocol.datagramReceived(datagram, None)

        self.assertEqual(1, len(out))

        eventDict = out[-1]
        self.assertEqual(u'myhost.example.org', eventDict['hostname'])
