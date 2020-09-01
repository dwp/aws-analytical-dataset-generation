from steps import generate_analytical_dataset
from steps.generate_analytical_dataset import sanitize, validate, retrieve_id, retrieve_last_modified_date_time, retrieve_date_time_element, replace_element_value_wit_key_value_pair, wrap_dates,get_valid_parsed_date_time,format_date_to_valid_outgoing_format
from pyspark.sql import SparkSession
import json
import pytest
from pyspark.sql import Row
from datetime import datetime


def test_sanitisation_processor_removes_desired_chars_in_collections():
    input_collection =  """{"fieldA":"a$\u0000","_archivedDateTime":"b","_archived":"c"}"""
    expected =  '{"fieldA":"ad_","_removedDateTime":"b","_removed":"c"}'
    actual = sanitize(input_collection, "", "")
    assert expected == actual

# TODO Check how is this working in Kotlin """{"message":{"db":"penalties-and-deductions","collection":"sanction"},"data":{"carriage":"\\r","newline":"\\n","superEscaped":"\\\r\\\n"}}"""
def test_sanitisation_processor_will_not_remove_multi_escaped_newlines():
    input_json =  """{"message":{"db":"penalties-and-deductions","collection":"sanction"},"data":{"carriage":"\\\\r","newline":"\\\\n","superEscaped":"\\\\r\\\\n"}}"""
    actual = sanitize(input_json,"penalties-and-deductions", "sanction" )
    assert input_json == actual


def test_sanitisatio_processor_removes_desired_chars_from_specific_collections(input_json, expected_json):
    input_json_dump = json.dumps(input_json)
    expected = json.dumps(expected_json)
    actual = sanitize(input_json_dump, "penalties-and-deductions", "sanction")
    assert expected == actual


def test_sanitisation_processor_does_not_remove_chars_from_other_collections(input_json, expected_json):
    input_json_dump = json.dumps(input_json)
    expected = json.dumps(expected_json)
    actual = sanitize(input_json_dump, "", "")
    assert expected != actual

@pytest.fixture(scope="module")
def input_json():
    input_string = """{
              "_id": {
                "declarationId": "47a4fad9-49af-4cb2-91b0-0056e2ac0eef\\r"
              },
              "type": "addressDeclaration\\n",
              "contractId": "aa16e682-fbd6-4fe3-880b-118ac09f992a\\r\\n",
              "addressNumber": {
                "type": "AddressLine",
                "cryptoId": "bd88a5f9-ab47-4ae0-80bf-e53908457b60"
              },
              "addressLine2": null,
              "townCity": {
                "type": "AddressLine",
                "cryptoId": "9ca3c63c-cbfc-452a-88fd-bb97f856fe60"
              },
              "postcode": "SM5 2LE",
              "processId": "3b313df5-96bc-40ff-8128-07d496379664",
              "effectiveDate": {
                "type": "SPECIFIC_EFFECTIVE_DATE",
                "date": 20150320,
                "knownDate": 20150320
              },
              "paymentEffectiveDate": {
                "type": "SPECIFIC_EFFECTIVE_DATE\\r\\n",
                "date": 20150320,
                "knownDate": 20150320
              },
              "createdDateTime": {
                "$date": "2015-03-20T12:23:25.183Z"
              },
              "_version": 2,
              "_lastModifiedDateTime": {
                "$date": "2016-06-23T05:12:29.624Z"
              }
        }"""
    input_json = json.loads(input_string)
    return input_json

@pytest.fixture(scope="module")
def expected_json():
    expected =  """
              {
              "_id": {
               "declarationId": "47a4fad9-49af-4cb2-91b0-0056e2ac0eef"
              },
              "type": "addressDeclaration",
              "contractId": "aa16e682-fbd6-4fe3-880b-118ac09f992a",
              "addressNumber": {
               "type": "AddressLine",
                "cryptoId": "bd88a5f9-ab47-4ae0-80bf-e53908457b60"
              },
              "addressLine2": null,
              "townCity": {
               "type": "AddressLine",
               "cryptoId": "9ca3c63c-cbfc-452a-88fd-bb97f856fe60"
              },
              "postcode": "SM5 2LE",
              "processId": "3b313df5-96bc-40ff-8128-07d496379664",
              "effectiveDate": {
               "type": "SPECIFIC_EFFECTIVE_DATE",
               "date": 20150320,
               "knownDate": 20150320
              },
              "paymentEffectiveDate": {
               "type": "SPECIFIC_EFFECTIVE_DATE",
               "date": 20150320,
               "knownDate": 20150320
              },
              "createdDateTime": {
               "d_date": "2015-03-20T12:23:25.183Z"
              },
              "_version": 2,
              "_lastModifiedDateTime": {
               "d_date": "2016-06-23T05:12:29.624Z"
              }
              }"""
    expected_json = json.loads(expected)
    return expected_json

def test_if_decrypted_dbObject_is_a_valid_json():
    id = {"someId":"RANDOM_GUID","declarationId":1234}
    decrypted_object = {"_id": id, "type": "addressDeclaration", "contractId": 1234, "addressNumber": {"type": "AddressLine", "cryptoId": 1234}, "addressLine2": None, "townCity": {"type": "AddressLine", "cryptoId": 1234}, "postcode": "SM5 2LE", "processId": 1234, "effectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "paymentEffectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "createdDateTime": {"$date": "2015-03-20T12:23:25.183Z", "_archivedDateTime": "should be replaced by _removedDateTime"}, "_version": 2, "_archived": "should be replaced by _removed", "unicodeNull": "\u0000", "unicodeNullwithText": "some\u0000text", "lineFeedChar": "\n", "lineFeedCharWithText": "some\ntext", "carriageReturn": "\r", "carriageReturnWithText": "some\rtext", "carriageReturnLineFeed": "\r\n", "carriageReturnLineFeedWithText": "some\r\ntext", "_lastModifiedDateTime": "2019-07-04T07:27:35.104+0000"}
    decrypted_str = json.dumps(decrypted_object)
    actual_json = validate(decrypted_str)
    actual = json.loads(actual_json)
    assert actual is not None

def test_if_decrypted_dbObject_is_a_valid_json_with_primitive_id():
    id = 'JSON_PRIMITIVE_STRING'
    decrypted_object = {"_id": id, "type": "addressDeclaration", "contractId": 1234, "addressNumber": {"type": "AddressLine", "cryptoId": 1234}, "addressLine2": None, "townCity": {"type": "AddressLine", "cryptoId": 1234}, "postcode": "SM5 2LE", "processId": 1234, "effectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "paymentEffectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "createdDateTime": {"$date": "2015-03-20T12:23:25.183Z", "_archivedDateTime": "should be replaced by _removedDateTime"}, "_version": 2, "_archived": "should be replaced by _removed", "unicodeNull": "\u0000", "unicodeNullwithText": "some\u0000text", "lineFeedChar": "\n", "lineFeedCharWithText": "some\ntext", "carriageReturn": "\r", "carriageReturnWithText": "some\rtext", "carriageReturnLineFeed": "\r\n", "carriageReturnLineFeedWithText": "some\r\ntext", "_lastModifiedDateTime": "2019-07-04T07:27:35.104+0000"}
    decrypted_str = json.dumps(decrypted_object)
    actual = validate(decrypted_str)
    assert actual is not None

def test_if_decrypted_dbObject_is_a_valid_json_with_object_id():
    id = {"someId":"RANDOM_GUID","declarationId":1234}
    decrypted_object = {"_id": id, "type": "addressDeclaration", "contractId": 1234, "addressNumber": {"type": "AddressLine", "cryptoId": 1234}, "addressLine2": None, "townCity": {"type": "AddressLine", "cryptoId": 1234}, "postcode": "SM5 2LE", "processId": 1234, "effectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "paymentEffectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "createdDateTime": {"$date": "2015-03-20T12:23:25.183Z", "_archivedDateTime": "should be replaced by _removedDateTime"}, "_version": 2, "_archived": "should be replaced by _removed", "unicodeNull": "\u0000", "unicodeNullwithText": "some\u0000text", "lineFeedChar": "\n", "lineFeedCharWithText": "some\ntext", "carriageReturn": "\r", "carriageReturnWithText": "some\rtext", "carriageReturnLineFeed": "\r\n", "carriageReturnLineFeedWithText": "some\r\ntext", "_lastModifiedDateTime": "2019-07-04T07:27:35.104+0000"}
    decrypted_str = json.dumps(decrypted_object)
    actual = validate(decrypted_str)
    assert actual is not None

# def Should_Log_Error_If_Decrypted_DbObject_Is_A_InValid_Json
# def Should_Log_Error_If_Decrypted_DbObject_Is_A_JsonPrimitive

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

#def Should_Log_Error_If_DbObject_Doesnt_Have_Id():

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
    assert new_json == actual


def test_format_all_unwrapped_dates():
    dateOne = "2019-12-14T15:01:02.000+0000"
    dateTwo = "2018-12-14T15:01:02.000+0000"
    dateThree = "2017-12-14T15:01:02.000+0000"
    dateFour = "2016-12-14T15:01:02.000+0000"

    old_json = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": dateOne,
        "createdDateTime": dateTwo,
        "_removedDateTime": dateThree,
        "_archivedDateTime": dateFour
    }

    formattedDateOne = "2019-12-14T15:01:02.000Z"
    formattedDateTwo = "2018-12-14T15:01:02.000Z"
    formattedDateThree = "2017-12-14T15:01:02.000Z"
    formattedDateFour = "2016-12-14T15:01:02.000Z"

    new_json = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": {"$date": formattedDateOne},
        "createdDateTime": {"$date": formattedDateTwo},
        "_removedDateTime": {"$date": formattedDateThree},
        "_archivedDateTime": {"$date": formattedDateFour}
    }
    actual = wrap_dates(old_json)
    assert new_json == actual

def test_keep_wrapped_dates_within_wrapper():
    dateOne = "2019-12-14T15:01:02.000Z"
    dateTwo = "2018-12-14T15:01:02.000Z"
    dateThree = "2017-12-14T15:01:02.000Z"
    dateFour = "2016-12-14T15:01:02.000Z"

    oldJson = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": {"$date": dateOne},
        "createdDateTime": {"$date": dateTwo},
        "_removedDateTime": {"$date": dateThree},
        "_archivedDateTime": {"$date": dateFour}
    }

    newJson = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": {"$date": dateOne},
        "createdDateTime": {"$date": dateTwo},
        "_removedDateTime": {"$date": dateThree},
        "_archivedDateTime": {"$date": dateFour}
    }
    actual = wrap_dates(oldJson)
    assert newJson == actual

def test_format_all_wrapped_dates():
    dateOne = "2019-12-14T15:01:02.000+0000"
    dateTwo = "2018-12-14T15:01:02.000+0000"
    dateThree = "2017-12-14T15:01:02.000+0000"
    dateFour = "2016-12-14T15:01:02.000+0000"

    oldJson = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": {"$date": dateOne},
        "createdDateTime": {"$date": dateTwo},
        "_removedDateTime": {"$date": dateThree},
        "_archivedDateTime": {"$date": dateFour}
    }

    formattedDateOne = "2019-12-14T15:01:02.000Z"
    formattedDateTwo = "2018-12-14T15:01:02.000Z"
    formattedDateThree = "2017-12-14T15:01:02.000Z"
    formattedDateFour = "2016-12-14T15:01:02.000Z"

    newJson = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": {"$date": formattedDateOne},
        "createdDateTime": {"$date": formattedDateTwo},
        "_removedDateTime": {"$date": formattedDateThree},
        "_archivedDateTime": {"$date": formattedDateFour}
    }
    actual = wrap_dates(oldJson)
    assert newJson == actual

def test_allow_for_missing_created_removed_and_archived_dates():
    dateOne = "2019-12-14T15:01:02.000Z"

    oldJson = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": dateOne
    }

    newJson = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": {"$date": dateOne}
    }
    actual = wrap_dates(oldJson)
    assert newJson == actual

def test_allow_for_empty_created_removed_and_archived_dates():
    dateOne = "2019-12-14T15:01:02.000Z"

    oldJson = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": dateOne,
        "createdDateTime": "",
        "_removedDateTime": "",
        "_archivedDateTime": ""
    }

    newJson = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": {"$date": dateOne},
        "createdDateTime": "",
        "_removedDateTime": "",
        "_archivedDateTime": ""
    }
    actual = wrap_dates(oldJson)
    assert newJson == actual

def test_allow_for_null_created_removed_and_archived_dates():
    dateOne = "2019-12-14T15:01:02.000Z"

    oldJson = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": dateOne,
        "createdDateTime": None,
        "_removedDateTime": None,
        "_archivedDateTime": None
    }

    newJson = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": {"$date": dateOne},
        "createdDateTime": None,
        "_removedDateTime": None,
        "_archivedDateTime": None
    }
    actual = wrap_dates(oldJson)
    assert newJson == actual

def test_create_last_modified_if_missing_dates():
    epoch = "1980-01-01T00:00:00.000Z"

    oldJson = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"}
    }

    newJson = {
        "_id":{"test_key_a":"test_value_a","test_key_b":"test_value_b"},
        "_lastModifiedDateTime": {"$date": epoch}
    }
    actual = wrap_dates(oldJson)
    assert newJson == actual

def test_parse_valid_incoming_date_format():
    dateOne = "2019-12-14T15:01:02.000+0000"
    expected = datetime.strptime(dateOne,'%Y-%m-%dT%H:%M:%S.%f%z')
    actual = get_valid_parsed_date_time(dateOne)
    assert expected == actual

def test_parse_valid_outgoing_date_format():
    dateOne = "2019-12-14T15:01:02.000Z"
    expected = datetime.strptime(dateOne,'%Y-%m-%dT%H:%M:%S.%fZ')
    actual = get_valid_parsed_date_time(dateOne)
    assert expected == actual

#def Should_Throw_Error_With_Invalid_Date_Format
#def Should_Return_Timestamp_Of_Valid_Date
#def Should_Return_Timestamp_Of_Valid_Date

def test_change_incoming_format_date_to_outgoing_format():
    dateOne = "2019-12-14T15:01:02.000+0000"
    expected = "2019-12-14T15:01:02.000Z"
    actual = format_date_to_valid_outgoing_format(dateOne)
    assert expected == actual

def test_not_change_date_already_in_outgoing_format():
    dateOne = "2019-12-14T15:01:02.000Z"
    expected = "2019-12-14T15:01:02.000Z"
    actual = format_date_to_valid_outgoing_format(dateOne)
    assert expected == actual

def test_main(monkeypatch):
    generate_analytical_dataset.get_plaintext_key_calling_dks = mock_get_plaintext_key_calling_dks
    monkeypatch.setattr(generate_analytical_dataset, 'get_published_db_name', mock_get_published_db_name)
    monkeypatch.setattr(generate_analytical_dataset, 'get_staging_db_name', mock_get_staging_db_name)
    monkeypatch.setattr(generate_analytical_dataset, 'get_tables', mock_get_tables)
    monkeypatch.setattr(generate_analytical_dataset, 'get_spark_session', mock_get_spark_session)
    monkeypatch.setattr(generate_analytical_dataset, 'get_dataframe_from_staging', mock_get_dataframe_from_staging)
    monkeypatch.setattr(generate_analytical_dataset, 'get_plaintext_key_calling_dks', mock_get_plaintext_key_calling_dks)
    monkeypatch.setattr(generate_analytical_dataset, 'persist_json', mock_persist_json)
    monkeypatch.setattr(generate_analytical_dataset, 'create_hive_on_published', mock_create_hive_on_published)
    monkeypatch.setattr(generate_analytical_dataset, 'retrieve_secrets', mock_retrieve_secrets)
    monkeypatch.setattr(generate_analytical_dataset, 'get_collections', mock_get_collections)
    monkeypatch.setattr(generate_analytical_dataset, 'tag_objects', mock_tag_objects)
    generate_analytical_dataset.main()

def mock_get_spark_session():
    spark = (
        SparkSession.builder.master('local[*]')
            .config("spark.sql.parquet.binaryAsString", "true")
            .appName("aws-analytical-dataset-generator-test")
            .enableHiveSupport()
            .getOrCreate()
    )
    return spark

def mock_retrieve_secrets():
    return {}

def mock_get_collections(secrets_response):
    return {}
def mock_tag_objects(s3_publish_bucket, prefix, collection_name, tag_value):
    return ''

def mock_get_tables(database_name):
    return ['table1']

def mock_get_published_db_name():
    return 'published'

def mock_get_staging_db_name():
    return 'staging'

def mock_get_dataframe_from_staging(adg_hive_select_query, spark):
    with open('test_message.json', 'r') as file:
        data = json.load(file)
        dt_string = json.dumps(data)
        data_row = Row('data')
        data_rows =[ data_row(dt_string)]
        user_df = mock_get_spark_session().createDataFrame(data_rows)
        user_df.show()
        return user_df

def mock_get_plaintext_key_calling_dks(r,keys_map):
    r['plain_text_key'] = 'czMQLgW/OrzBZwFV9u4EBA=='
    return r

def mock_persist_json(S3_PUBLISH_BUCKET, table_to_process, values):
    return ''

def mock_create_hive_on_published(parquet_location, published_database_name, spark, table_to_process):
    return ''

def mock_get_staging_db_name():
    return 'staging'

def mock_get_dataframe_from_staging(adg_hive_select_query, spark):
    with open('test_message.json', 'r') as file:
        data = json.load(file)
        dt_string = json.dumps(data)
        data_row = Row('data')
        data_rows =[ data_row(dt_string)]
        user_df = mock_get_spark_session().createDataFrame(data_rows)
        user_df.show()
        return user_df

def mock_get_plaintext_key_calling_dks(r,keys_map):
    r['plain_text_key'] = 'czMQLgW/OrzBZwFV9u4EBA=='
    return r

def mock_persist_parquet(S3_PUBLISH_BUCKET, table_to_process, values):
    return ''

def mock_create_hive_on_published(parquet_location, published_database_name, spark, table_to_process):
    return ''
