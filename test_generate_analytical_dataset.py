from generate_analytical_dataset import sanitize, validate, retrieve_id, retrieve_last_modified_date_time, retrieve_date_time_element, replace_element_value_wit_key_value_pair, wrap_dates
import json


def test_if_decrypted_dbObject_is_a_valid_json():
    id = {"someId":"RANDOM_GUID","declarationId":1234}
    decrypted_object = {"_id": id, "type": "addressDeclaration", "contractId": 1234, "addressNumber": {"type": "AddressLine", "cryptoId": 1234}, "addressLine2": None, "townCity": {"type": "AddressLine", "cryptoId": 1234}, "postcode": "SM5 2LE", "processId": 1234, "effectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "paymentEffectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "createdDateTime": {"$date": "2015-03-20T12:23:25.183Z", "_archivedDateTime": "should be replaced by _removedDateTime"}, "_version": 2, "_archived": "should be replaced by _removed", "unicodeNull": "\u0000", "unicodeNullwithText": "some\u0000text", "lineFeedChar": "\n", "lineFeedCharWithText": "some\ntext", "carriageReturn": "\r", "carriageReturnWithText": "some\rtext", "carriageReturnLineFeed": "\r\n", "carriageReturnLineFeedWithText": "some\r\ntext", "_lastModifiedDateTime": "2019-07-04T07:27:35.104+0000"}
    input = json.dumps(decrypted_object)
    actual = validate(input)
    assert actual is not None

def test_if_decrypted_dbObject_is_a_valid_json_with_primitive_id():
    id = 'JSON_PRIMITIVE_STRING'
    decrypted_object = {"_id": id, "type": "addressDeclaration", "contractId": 1234, "addressNumber": {"type": "AddressLine", "cryptoId": 1234}, "addressLine2": None, "townCity": {"type": "AddressLine", "cryptoId": 1234}, "postcode": "SM5 2LE", "processId": 1234, "effectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "paymentEffectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "createdDateTime": {"$date": "2015-03-20T12:23:25.183Z", "_archivedDateTime": "should be replaced by _removedDateTime"}, "_version": 2, "_archived": "should be replaced by _removed", "unicodeNull": "\u0000", "unicodeNullwithText": "some\u0000text", "lineFeedChar": "\n", "lineFeedCharWithText": "some\ntext", "carriageReturn": "\r", "carriageReturnWithText": "some\rtext", "carriageReturnLineFeed": "\r\n", "carriageReturnLineFeedWithText": "some\r\ntext", "_lastModifiedDateTime": "2019-07-04T07:27:35.104+0000"}
    input = json.dumps(decrypted_object)
    expected_object = {"_id": {"$oid" : id}, "type": "addressDeclaration", "contractId": 1234, "addressNumber": {"type": "AddressLine", "cryptoId": 1234}, "addressLine2": None, "townCity": {"type": "AddressLine", "cryptoId": 1234}, "postcode": "SM5 2LE", "processId": 1234, "effectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "paymentEffectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "createdDateTime": {"$date": "2015-03-20T12:23:25.183Z", "_archivedDateTime": "should be replaced by _removedDateTime"}, "_version": 2, "_archived": "should be replaced by _removed", "unicodeNull": "\u0000", "unicodeNullwithText": "some\u0000text", "lineFeedChar": "\n", "lineFeedCharWithText": "some\ntext", "carriageReturn": "\r", "carriageReturnWithText": "some\rtext", "carriageReturnLineFeed": "\r\n", "carriageReturnLineFeedWithText": "some\r\ntext", "_lastModifiedDateTime": "2019-07-04T07:27:35.104+0000"}
    actual = validate(input)
    assert actual is not None

def test_if_decrypted_dbObject_is_a_valid_json_with_object_id():
    id = {"someId":"RANDOM_GUID","declarationId":1234}
    decrypted_object = {"_id": id, "type": "addressDeclaration", "contractId": 1234, "addressNumber": {"type": "AddressLine", "cryptoId": 1234}, "addressLine2": None, "townCity": {"type": "AddressLine", "cryptoId": 1234}, "postcode": "SM5 2LE", "processId": 1234, "effectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "paymentEffectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "createdDateTime": {"$date": "2015-03-20T12:23:25.183Z", "_archivedDateTime": "should be replaced by _removedDateTime"}, "_version": 2, "_archived": "should be replaced by _removed", "unicodeNull": "\u0000", "unicodeNullwithText": "some\u0000text", "lineFeedChar": "\n", "lineFeedCharWithText": "some\ntext", "carriageReturn": "\r", "carriageReturnWithText": "some\rtext", "carriageReturnLineFeed": "\r\n", "carriageReturnLineFeedWithText": "some\r\ntext", "_lastModifiedDateTime": "2019-07-04T07:27:35.104+0000"}
    input = json.dumps(decrypted_object)
    actual = validate(input)
    assert actual is not None

# def test_log_error_if_decrypted_dbObject_is_a_invalid_json
# def test_log_error_if_decrypted_dbObject_is_a_jsonprimitive

def test_retrieve_id_if_dbobject_is_a_valid_json():
    date_one = '2019-12-14T15:01:02.000+0000'
    date_two = '2018-12-14T15:01:02.000+0000'
    decrypted_db_object = {"_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
                           "_lastModifiedDateTime": date_one,
                           "createdDateTime": date_two}
    id = retrieve_id(decrypted_db_object)
    assert id is not None

def test_retrieve_lastmodifieddatetime_if_dbobject_is_a_valid_string():
    date_one = '2019-12-14T15:01:02.000+0000'
    date_two = '2018-12-14T15:01:02.000+0000'
    decrypted_db_object = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": date_one,
        "createdDateTime": date_two
    }
    last_modified_date_time = retrieve_last_modified_date_time(decrypted_db_object)
    print(f'actual is {last_modified_date_time}')
    assert  date_one == last_modified_date_time


def test_retrieve_lastmodifieddatetime_if_dbObject_is_a_valid_json_object():
    date_one = '2019-12-14T15:01:02.000+0000'
    date_two = '2018-12-14T15:01:02.000+0000'
    decrypted_db_object = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": {"$date": date_one},
    "createdDateTime": {"$date": date_two}
    }
    last_modified_date_time = retrieve_last_modified_date_time(decrypted_db_object)
    assert date_one == last_modified_date_time

def test_retrieve_createddatetime_when_present_and_lastmodifieddatetime_is_missing():
    date_one = '2019-12-14T15:01:02.000+0000'
    date_two = '2018-12-14T15:01:02.000+0000'
    decrypted_db_object = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": {"date": date_one},
        "createdDateTime": {"$date": date_two}
    }
    last_modified_date_time = retrieve_last_modified_date_time(decrypted_db_object)
    print(f'actual is {last_modified_date_time}')
    assert date_two == last_modified_date_time

def test_retrieve_createddatetime_when_present_and_lastmodifieddatetime_is_empty():
    date_one = '2019-12-14T15:01:02.000+0000'
    decrypted_db_object = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": "",
        "createdDateTime": {"$date": date_one}
    }
    last_modified_date_time = retrieve_last_modified_date_time(decrypted_db_object)
    assert date_one == last_modified_date_time

def test_retrieve_createddatetime_when_present_and_lastmodifieddatetime_is_null():
    date_one = '2019-12-14T15:01:02.000+0000'
    decrypted_db_object = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": None,
        "createdDateTime": {"$date": date_one}
    }
    last_modified_date_time = retrieve_last_modified_date_time(decrypted_db_object)
    assert date_one == last_modified_date_time

def test_retrieve_epoch_when_createddatetime_and_lastmodifieddatetime_are_missing():
    epoch = "1980-01-01T00:00:00.000Z"
    decrypted_db_object = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"}
    }
    last_modified_date_time = retrieve_last_modified_date_time(decrypted_db_object)
    assert epoch == last_modified_date_time

def test_retrieve_epoch_when_createddatetime_and_lastmodifieddatetime_are_invalid_json_objects():
    epoch = "1980-01-01T00:00:00.000Z"
    dateOne = "2019-12-14T15:01:02.000+0000"
    dateTwo = "2018-12-14T15:01:02.000+0000"
    decrypted_db_object = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": {"date": dateOne},
        "createdDateTime": {"date": dateTwo}
    }
    last_modified_date_time = retrieve_last_modified_date_time(decrypted_db_object)
    assert epoch == last_modified_date_time

def test_retrieve_epoch_when_createddatetime_and_lastmodifieddatetime_are_empty():
    epoch = "1980-01-01T00:00:00.000Z"
    decrypted_db_object = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": {"date": ""},
        "createdDateTime": {"date": ""}
    }
    last_modified_date_time = retrieve_last_modified_date_time(decrypted_db_object)
    assert epoch == last_modified_date_time

def test_retrieve_epoch_when_createddatetime_and_lastmodifieddatetime_are_null():
    epoch = "1980-01-01T00:00:00.000Z"
    decrypted_db_object = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": {"date": None},
        "createdDateTime": {"date": None}
    }
    last_modified_date_time = retrieve_last_modified_date_time(decrypted_db_object)
    assert epoch == last_modified_date_time

def test_retrieve_value_string_when_date_element_is_string():
    expected = "A Date"
    decrypted_db_object = {
                   "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
                   "dateTimeTestElement": expected
                }
    actual = retrieve_date_time_element('dateTimeTestElement',decrypted_db_object)
    assert expected == actual

def test_retrieve_value_string_when_date_element_is_valid_object():
    expected = "A Date"
    decrypted_db_object = {
                   "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
                   "dateTimeTestElement": {"$date": expected}
                }
    actual = retrieve_date_time_element('dateTimeTestElement',decrypted_db_object)
    assert expected == actual

def test_retrieve_empty_string_when_date_element_is_invalid_object():
    expected = ""
    decrypted_db_object = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "dateTimeTestElement": {"date": expected}
    }
    actual = retrieve_date_time_element('dateTimeTestElement',decrypted_db_object)
    assert expected == actual

def test_retrieve_empty_string_when_date_element_is_null():
    expected = ""
    decrypted_db_object = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "dateTimeTestElement": None
    }
    actual = retrieve_date_time_element('dateTimeTestElement',decrypted_db_object)
    assert expected == actual

#def test_log_error_if_dbObject_doesnt_have_id():

def test_replace_value_when_current_value_is_string():
    old_date = "2019-12-14T15:01:02.000+0000"
    new_date = "2018-12-14T15:01:02.000+0000"

    old_json = {
                   "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
                   "_lastModifiedDateTime": old_date
                }

    new_json = {
                    "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
                    "_lastModifiedDateTime": {"$date": new_date}
                }
    actual = replace_element_value_wit_key_value_pair(old_json, '_lastModifiedDateTime', '$date', new_date )
    assert new_json == actual

def test_replace_value_when_current_value_is_object_with_matching_key():
    old_date = "2019-12-14T15:01:02.000+0000"
    new_date = "2018-12-14T15:01:02.000+0000"

    old_json = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": {"$date": old_date}
    }

    new_json = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": {"$date": new_date}
    }
    actual = replace_element_value_wit_key_value_pair(old_json, '_lastModifiedDateTime', '$date', new_date )
    assert new_json == actual

def test_replace_value_when_current_value_is_object_with_no_matching_key():
    old_date = "2019-12-14T15:01:02.000+0000"
    new_date = "2018-12-14T15:01:02.000+0000"

    old_json = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": {"notDate": old_date}
    }

    new_json = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": {"$date": new_date}
    }
    actual = replace_element_value_wit_key_value_pair(old_json, '_lastModifiedDateTime', '$date', new_date )
    assert new_json == actual

def test_replace_value_when_current_value_is_object_with_no_multiple_keys():
    old_date = "2019-12-14T15:01:02.000+0000"
    new_date = "2018-12-14T15:01:02.000+0000"
    old_json = {
                   "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
                   "_lastModifiedDateTime": {"notDate": old_date, "notDateTwo": old_date}
                }

    new_json = {
                    "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
                    "_lastModifiedDateTime": {"$date": new_date}
                }
    actual = replace_element_value_wit_key_value_pair(old_json, '_lastModifiedDateTime', '$date', new_date )
    assert new_json == actual

def test_wrap_all_dates():
    date_one = "2019-12-14T15:01:02.000Z"
    date_two = "2018-12-14T15:01:02.000Z"
    date_three = "2017-12-14T15:01:02.000Z"
    date_four = "2016-12-14T15:01:02.000Z"

    old_json = {
                   "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
                   "_lastModifiedDateTime": date_one,
                   "createdDateTime": date_two,
                   "_removedDateTime": date_three,
                   "_archivedDateTime": date_four
                }
    new_json = {
                    "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
                    "_lastModifiedDateTime": {"$date": date_one},
                    "createdDateTime": {"$date": date_two},
                    "_removedDateTime": {"$date": date_three},
                    "_archivedDateTime": {"$date": date_four}
                }
# TODO do we need to return  last modified time as tuple
    actual = wrap_dates(old_json)
    print(f'actual is {actual}')
    assert new_json == actual
