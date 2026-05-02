import json
test_string = '{"first_name": "Bryan", "last_name": "Nguyen"}'
test_json = json.loads(test_string)
print(test_json["first_name"])
print(test_json["last_name"])

test_json = {
    "first_name": "nghi",
    "last_name": "nguyen",
    "test": {}
}
test_string = json.dumps(test_json)
print(test_string)
print(json.loads(test_string))