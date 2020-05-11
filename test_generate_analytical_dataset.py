import generate_analytical_dataset
from generate_analytical_dataset import sanitize, validate, retrieve_id, retrieve_last_modified_date_time, retrieve_date_time_element, replace_element_value_wit_key_value_pair, wrap_dates
from pyspark.sql import SparkSession
import json
from pyspark.sql import Row


def test_sanitisation_processor_removes_desired_chars_in_collections():
    input =  """{"fieldA":"a$\u0000","_archivedDateTime":"b","_archived":"c"}"""
    expected =  '{"fieldA":"ad_","_removedDateTime":"b","_removed":"c"}'
    decrypted_str = json.dumps(input)
    msg = {"decrypted":input, "db_name":"","collection_name":""}
    actual = sanitize(msg)
    print(f'actualllllly is {actual}')
    assert expected == actual

# TODO Check how is this working in Kotlin """{"message":{"db":"penalties-and-deductions","collection":"sanction"},"data":{"carriage":"\\r","newline":"\\n","superEscaped":"\\\r\\\n"}}"""
def test_sanitisation_processor_will_not_remove_multi_escaped_newlines():
    input =  """{"message":{"db":"penalties-and-deductions","collection":"sanction"},"data":{"carriage":"\\\\r","newline":"\\\\n","superEscaped":"\\\\r\\\\n"}}"""
    msg = {"decrypted":input, "db_name":"penalties-and-deductions","collection_name":"sanction"}
    actual = sanitize(msg)
    assert input == actual


def test_sanitisatio_processor_removes_desired_chars_from_specific_collections():
    input = json.dumps(get_input())
    expected = json.dumps(get_expected())
    actual = sanitize(input, "penalties-and-deductions", "sanction")
    assert expected == actual


def test_sanitisation_processor_does_not_remove_chars_from_other_collections():
    input = json.dumps(get_input())
    expected = json.dumps(get_expected())
    actual = sanitize(input, "", "")
    assert expected != actual


def get_input():
    input = """{
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
    return json.loads(input)

def get_expected():
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
    return json.loads(expected)

def test_if_decrypted_dbObject_is_a_valid_json():
    id = {"someId":"RANDOM_GUID","declarationId":1234}
    decrypted_object = {"_id": id, "type": "addressDeclaration", "contractId": 1234, "addressNumber": {"type": "AddressLine", "cryptoId": 1234}, "addressLine2": None, "townCity": {"type": "AddressLine", "cryptoId": 1234}, "postcode": "SM5 2LE", "processId": 1234, "effectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "paymentEffectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "createdDateTime": {"$date": "2015-03-20T12:23:25.183Z", "_archivedDateTime": "should be replaced by _removedDateTime"}, "_version": 2, "_archived": "should be replaced by _removed", "unicodeNull": "\u0000", "unicodeNullwithText": "some\u0000text", "lineFeedChar": "\n", "lineFeedCharWithText": "some\ntext", "carriageReturn": "\r", "carriageReturnWithText": "some\rtext", "carriageReturnLineFeed": "\r\n", "carriageReturnLineFeedWithText": "some\r\ntext", "_lastModifiedDateTime": "2019-07-04T07:27:35.104+0000"}
    decrypted_str = json.dumps(decrypted_object)
    msg = {"decrypted":decrypted_str}
    actual = validate(msg)
    assert actual['decrypted'] is not None

def test_if_decrypted_dbObject_is_a_valid_json_with_primitive_id():
    id = 'JSON_PRIMITIVE_STRING'
    decrypted_object = {"_id": id, "type": "addressDeclaration", "contractId": 1234, "addressNumber": {"type": "AddressLine", "cryptoId": 1234}, "addressLine2": None, "townCity": {"type": "AddressLine", "cryptoId": 1234}, "postcode": "SM5 2LE", "processId": 1234, "effectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "paymentEffectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "createdDateTime": {"$date": "2015-03-20T12:23:25.183Z", "_archivedDateTime": "should be replaced by _removedDateTime"}, "_version": 2, "_archived": "should be replaced by _removed", "unicodeNull": "\u0000", "unicodeNullwithText": "some\u0000text", "lineFeedChar": "\n", "lineFeedCharWithText": "some\ntext", "carriageReturn": "\r", "carriageReturnWithText": "some\rtext", "carriageReturnLineFeed": "\r\n", "carriageReturnLineFeedWithText": "some\r\ntext", "_lastModifiedDateTime": "2019-07-04T07:27:35.104+0000"}
    decrypted_str = json.dumps(decrypted_object)
    msg = {"decrypted":decrypted_str}
    actual = validate(msg)
    assert actual is not None

def test_if_decrypted_dbObject_is_a_valid_json_with_object_id():
    id = {"someId":"RANDOM_GUID","declarationId":1234}
    decrypted_object = {"_id": id, "type": "addressDeclaration", "contractId": 1234, "addressNumber": {"type": "AddressLine", "cryptoId": 1234}, "addressLine2": None, "townCity": {"type": "AddressLine", "cryptoId": 1234}, "postcode": "SM5 2LE", "processId": 1234, "effectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "paymentEffectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "createdDateTime": {"$date": "2015-03-20T12:23:25.183Z", "_archivedDateTime": "should be replaced by _removedDateTime"}, "_version": 2, "_archived": "should be replaced by _removed", "unicodeNull": "\u0000", "unicodeNullwithText": "some\u0000text", "lineFeedChar": "\n", "lineFeedCharWithText": "some\ntext", "carriageReturn": "\r", "carriageReturnWithText": "some\rtext", "carriageReturnLineFeed": "\r\n", "carriageReturnLineFeedWithText": "some\r\ntext", "_lastModifiedDateTime": "2019-07-04T07:27:35.104+0000"}
    decrypted_str = json.dumps(decrypted_object)
    msg = {"decrypted":decrypted_str}
    actual = validate(msg)
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

def test_main(monkeypatch):
    generate_analytical_dataset.get_plaintext_key_calling_dks = mock_get_plaintext_key_calling_dks
    monkeypatch.setattr(generate_analytical_dataset, 'retrieve_secrets', mock_retrieve_secrets)
    monkeypatch.setattr(generate_analytical_dataset, 'get_published_db_name', mock_get_published_db_name)
    monkeypatch.setattr(generate_analytical_dataset, 'get_staging_db_name', mock_get_staging_db_name)
    monkeypatch.setattr(generate_analytical_dataset, 'get_tables', mock_get_tables)
    monkeypatch.setattr(generate_analytical_dataset, 'get_spark_session', mock_get_spark_session)
    monkeypatch.setattr(generate_analytical_dataset, 'get_dataframe_from_staging', mock_get_dataframe_from_staging)
    monkeypatch.setattr(generate_analytical_dataset, 'get_plaintext_key_calling_dks', mock_get_plaintext_key_calling_dks)
    monkeypatch.setattr(generate_analytical_dataset, 'persist_parquet', mock_persist_parquet)
    monkeypatch.setattr(generate_analytical_dataset, 'create_hive_on_published', mock_create_hive_on_published)
    generate_analytical_dataset.main()

def mock_retrieve_secrets():
    return {"S3_PUBLISH_BUCKET":"abcd"}

def mock_get_spark_session():
    spark = (
        SparkSession.builder.master('local[*]')
            .config("spark.sql.parquet.binaryAsString", "true")
            .appName("aws-analytical-dataset-generator-test")
            .enableHiveSupport()
            .getOrCreate()
    )
    return spark

def mock_get_tables(database_name):
    return ['table1']

def mock_get_published_db_name():
    return 'published'# TODO Check how is this working in Kotlin """{"message":{"db":"penalties-and-deductions","collection":"sanction"},"data":{"carriage":"\\r","newline":"\\n","superEscaped":"\\\r\\\n"}}"""
def test_sanitisation_processor_will_not_remove_multi_escaped_newlines():
    input =  """{"message":{"db":"penalties-and-deductions","collection":"sanction"},"data":{"carriage":"\\\\r","newline":"\\\\n","superEscaped":"\\\\r\\\\n"}}"""
    msg = {"decrypted":input, "db_name":"penalties-and-deductions","collection_name":"sanction"}
    actual = sanitize(msg)
    assert input == actual


def test_sanitisatio_processor_removes_desired_chars_from_specific_collections():
    input = json.dumps(get_input())
    expected = json.dumps(get_expected())
    actual = sanitize(input, "penalties-and-deductions", "sanction")
    assert expected == actual


def test_sanitisation_processor_does_not_remove_chars_from_other_collections():
    input = json.dumps(get_input())
    expected = json.dumps(get_expected())
    actual = sanitize(input, "", "")
    assert expected != actual


def get_input():
    input = """{
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
    return json.loads(input)

def get_expected():
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
    return json.loads(expected)

def test_if_decrypted_dbObject_is_a_valid_json():
    id = {"someId":"RANDOM_GUID","declarationId":1234}
    decrypted_object = {"_id": id, "type": "addressDeclaration", "contractId": 1234, "addressNumber": {"type": "AddressLine", "cryptoId": 1234}, "addressLine2": None, "townCity": {"type": "AddressLine", "cryptoId": 1234}, "postcode": "SM5 2LE", "processId": 1234, "effectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "paymentEffectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "createdDateTime": {"$date": "2015-03-20T12:23:25.183Z", "_archivedDateTime": "should be replaced by _removedDateTime"}, "_version": 2, "_archived": "should be replaced by _removed", "unicodeNull": "\u0000", "unicodeNullwithText": "some\u0000text", "lineFeedChar": "\n", "lineFeedCharWithText": "some\ntext", "carriageReturn": "\r", "carriageReturnWithText": "some\rtext", "carriageReturnLineFeed": "\r\n", "carriageReturnLineFeedWithText": "some\r\ntext", "_lastModifiedDateTime": "2019-07-04T07:27:35.104+0000"}
    decrypted_str = json.dumps(decrypted_object)
    msg = {"decrypted":decrypted_str}
    actual = validate(msg)
    assert actual['decrypted'] is not None

def test_if_decrypted_dbObject_is_a_valid_json_with_primitive_id():
    id = 'JSON_PRIMITIVE_STRING'
    decrypted_object = {"_id": id, "type": "addressDeclaration", "contractId": 1234, "addressNumber": {"type": "AddressLine", "cryptoId": 1234}, "addressLine2": None, "townCity": {"type": "AddressLine", "cryptoId": 1234}, "postcode": "SM5 2LE", "processId": 1234, "effectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "paymentEffectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "createdDateTime": {"$date": "2015-03-20T12:23:25.183Z", "_archivedDateTime": "should be replaced by _removedDateTime"}, "_version": 2, "_archived": "should be replaced by _removed", "unicodeNull": "\u0000", "unicodeNullwithText": "some\u0000text", "lineFeedChar": "\n", "lineFeedCharWithText": "some\ntext", "carriageReturn": "\r", "carriageReturnWithText": "some\rtext", "carriageReturnLineFeed": "\r\n", "carriageReturnLineFeedWithText": "some\r\ntext", "_lastModifiedDateTime": "2019-07-04T07:27:35.104+0000"}
    decrypted_str = json.dumps(decrypted_object)
    msg = {"decrypted":decrypted_str}
    actual = validate(msg)
    assert actual is not None

def test_if_decrypted_dbObject_is_a_valid_json_with_object_id():
    id = {"someId":"RANDOM_GUID","declarationId":1234}
    decrypted_object = {"_id": id, "type": "addressDeclaration", "contractId": 1234, "addressNumber": {"type": "AddressLine", "cryptoId": 1234}, "addressLine2": None, "townCity": {"type": "AddressLine", "cryptoId": 1234}, "postcode": "SM5 2LE", "processId": 1234, "effectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "paymentEffectiveDate": {"type": "SPECIFIC_EFFECTIVE_DATE", "date": 20150320, "knownDate": 20150320}, "createdDateTime": {"$date": "2015-03-20T12:23:25.183Z", "_archivedDateTime": "should be replaced by _removedDateTime"}, "_version": 2, "_archived": "should be replaced by _removed", "unicodeNull": "\u0000", "unicodeNullwithText": "some\u0000text", "lineFeedChar": "\n", "lineFeedCharWithText": "some\ntext", "carriageReturn": "\r", "carriageReturnWithText": "some\rtext", "carriageReturnLineFeed": "\r\n", "carriageReturnLineFeedWithText": "some\r\ntext", "_lastModifiedDateTime": "2019-07-04T07:27:35.104+0000"}
    decrypted_str = json.dumps(decrypted_object)
    msg = {"decrypted":decrypted_str}
    actual = validate(msg)
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

def test_main(monkeypatch):
    generate_analytical_dataset.get_plaintext_key_calling_dks = mock_get_plaintext_key_calling_dks
    monkeypatch.setattr(generate_analytical_dataset, 'retrieve_secrets', mock_retrieve_secrets)
    monkeypatch.setattr(generate_analytical_dataset, 'get_published_db_name', mock_get_published_db_name)
    monkeypatch.setattr(generate_analytical_dataset, 'get_staging_db_name', mock_get_staging_db_name)
    monkeypatch.setattr(generate_analytical_dataset, 'get_tables', mock_get_tables)
    monkeypatch.setattr(generate_analytical_dataset, 'get_spark_session', mock_get_spark_session)
    monkeypatch.setattr(generate_analytical_dataset, 'get_dataframe_from_staging', mock_get_dataframe_from_staging)
    monkeypatch.setattr(generate_analytical_dataset, 'get_plaintext_key_calling_dks', mock_get_plaintext_key_calling_dks)
    monkeypatch.setattr(generate_analytical_dataset, 'persist_parquet', mock_persist_parquet)
    monkeypatch.setattr(generate_analytical_dataset, 'create_hive_on_published', mock_create_hive_on_published)
    generate_analytical_dataset.main()

def mock_retrieve_secrets():
    return {"S3_PUBLISH_BUCKET":"abcd"}

def mock_get_spark_session():
    spark = (
        SparkSession.builder.master('local[*]')
            .config("spark.sql.parquet.binaryAsString", "true")
            .appName("aws-analytical-dataset-generator-test")
            .enableHiveSupport()
            .getOrCreate()
    )
    return spark

def mock_get_tables(database_name):
    return ['table1']

def mock_get_published_db_name():
    return 'published'

def mock_get_staging_db_name():
    return 'staging'

def mock_get_dataframe_from_staging(adg_hive_select_query, spark):
    spark = mock_get_spark_session()
    with open('test_message.json', 'r') as file:
        data = json.load(file)
        dt_string = json.dumps(data)
        #df =   pd.DataFrame({'data':[dt_string]})
        #print(f'df is {df.head()}')
        #return df
        data_row = Row('data')
        data_rows =[ data_row(dt_string)]
        user_df = spark.createDataFrame(data_rows)
        print(f'the dataframe from  the test is below ')
        user_df.show()
        return user_df

def mock_get_plaintext_key_calling_dks(r,keys_map):
    print(f'i am called heheeheheh')
    r['plain_text_key'] = 'czMQLgW/OrzBZwFV9u4EBA=='
    return r

def mock_persist_parquet(S3_PUBLISH_BUCKET, table_to_process, values):
    return ''

def mock_create_hive_on_published(parquet_location, published_database_name, spark, table_to_process):
    return ''

def mock_get_staging_db_name():
    return 'staging'

def mock_get_dataframe_from_staging(adg_hive_select_query, spark):
    spark = mock_get_spark_session()
    with open('test_message.json', 'r') as file:
        data = json.load(file)
        dt_string = json.dumps(data)
        #df =   pd.DataFrame({'data':[dt_string]})
        #print(f'df is {df.head()}')
        #return df
        data_row = Row('data')
        data_rows =[ data_row(dt_string)]
        user_df = spark.createDataFrame(data_rows)
        print(f'the dataframe from  the test is below ')
        user_df.show()
        return user_df

def mock_get_plaintext_key_calling_dks(r,keys_map):
    print(f'i am called heheeheheh')
    r['plain_text_key'] = 'czMQLgW/OrzBZwFV9u4EBA=='
    return r

def mock_persist_parquet(S3_PUBLISH_BUCKET, table_to_process, values):
    return ''

def mock_create_hive_on_published(parquet_location, published_database_name, spark, table_to_process):
    return ''
