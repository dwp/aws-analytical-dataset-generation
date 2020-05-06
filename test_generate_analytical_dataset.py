from generate_analytical_dataset import sanitize, just
import json
from jsondiff import diff



def test_sanitisation_processor_removes_desired_chars_in_collections():
    input =  """{"fieldA":"a$\u0000","_archivedDateTime":"b","_archived":"c"} """
    expected =  """{"fieldA":"ad_","_removedDateTime":"b","_removed":"c"} """
    actual = sanitize(input, "", "")
    expected_obj = json.loads(expected)
    actual_obj = json.loads(actual)
    assert expected_obj == actual_obj

# TODO Check how is this working in Kotlin """{"message":{"db":"penalties-and-deductions","collection":"sanction"},"data":{"carriage":"\\r","newline":"\\n","superEscaped":"\\\r\\\n"}}"""
def test_sanitisation_processor_will_not_remove_multi_escaped_newlines():
    input_decoded =  json.loads("""{"message":{"db":"penalties-and-deductions","collection":"sanction"},"data":{"carriage":"\\\\r","newline":"\\\\n","superEscaped":"\\\\r\\\\n"}}""", strict=False)
    input_encoded = json.dumps(input_decoded)
    actual = sanitize(input_encoded, "penalties-and-deductions", "sanction")
    assert input_encoded == actual


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






