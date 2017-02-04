import json

import habu

def do_req(uri, *args, **kwargs):
    route_data = {
        "/": {
            "_links": {
                "people": { "href": "/people" },
                "animals": { "href": "/animals" }
            }
        },
        "/people": {
            "_links": {
                "self": { "href": "/products" }
            },
            "_embedded": {
                "people": [
                    { "_links": { "self": { "href": "/people/clagraff" } }, "name": "Curtis", "age": 22 }
                ]
            },
            "total": 1
        },
        "/people/clagraff": {
            "_links": {
                "self": { "href": "/people/clagraff" }
            },
            "name": "Curtis",
            "age": 22
        }
    }
    return route_data[uri]


def main():
    habu.set_request_func(do_req)
    api = habu.enter("/")

    people = api.people()
    print("There are %i people" % people.total)

    for person in people.embedded.people:
        print("Hi! I am %s and I am %i years old" % (person.name, person.age))

    curtis = habu.enter("/people/clagraff")
    print(curtis)

if __name__ == "__main__":
    main()
