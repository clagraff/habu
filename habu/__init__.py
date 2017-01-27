import pprint
import warnings

import uri_parsing


def debug_request_func(uri, *args, **kwargs):
    """ An optional request function which will simply print its arguments. """
    msg = "request for %s" % uri
    if args:
        msg += " with %s" % str(args)
    if kwargs:
        msg += " with %s" % str(kwargs)

    print(msg)
    return {}


_embedded_empty_list_fallback = True
_request_func = None


def use_missing_embedded_fallback(bool_=True):
    """ Enable returning a list if accessing a missing embedded resource. """
    if not isinstance(bool_, bool):
        raise TypeError("'%s' must be a bool" % bool_.__class__.__name__)
    _embedded_empty_list_fallback = bool_


def set_request_func(callable_):
    """ Set the function to use when executing Link HTTP requests.

    The function will be called with a non-templated URI, along with
    any *args and/or **kwargs that are originally provided to the call.

    This function is your hook for executing an HTTP request against your API.
    You can use any HTTP request library you want, add in any authentication
    code, handle response errors, log data, etc.
    """
    if not callable(callable_):
        raise TypeError("'%s' must be callable" % callable_.__class__.__name__)
    global _request_func
    _request_func  = callable_


class Link(object):
    """ Represents a hyperlink to an accessible HAL resource.

    The `_rel` attribute is the `name` attribute of the Link if the link
    was unserialized from a list, or it is the key attribute that was parent
    to this link as an object.

    If `deprecation` is any value other than `None`, this link is considered
    decrepet.
    """
    def __init__(self):
        self._documentation = None
        self._rel = ""

        self.deprecation = None
        self.href = ""
        self.hreflang = "en-US"
        self.name = ""
        self.profile = ""
        self.templated = False
        self.title = ""
        self.type = "application/hal+json"

    def __call__(self, *args, **kwargs):
        """ Call the Link to attempt to retrieve its hyperlinked resource. """
        if not _request_func:
            raise RuntimeError(
                "Must set a request function using 'set_request_func'"
            )

        uri = self.href
        if self.templated:
            (uri, args, kwargs) = uri_parsing.parse_uri(self.href, *args, **kwargs)

        result = _request_func(uri, *args, **kwargs)
        return Resource(result)

    def unserialize(self, dict_):
        """ Unserialize a dictionary object into the current Link's attributes. """
        if not isinstance(dict_, dict):
            raise TypeError("'%s' must be a dict" % dict_.__class__.__name__)
        if "href" not in dict_:
            warnings.warn("missing HREF attribute in Link")
        for key, val in dict_.items():
            if key in self.__dict__:
                self.__dict__[key] = val
            else:
                warnings.warn("invalid Link attribute '%s' = '%s'" % (key, val))
        if self.deprecation:
            warnings.warn(
                "link rel '%s' has been deprecated; use at own risk" % self._rel
            )

    def __str__(self):
        """ Represent the current Link as a string. """
        return "Link(" + pprint.pformat(self.__dict__) + ")"


class CURIE(Link):
    def resolve(self, link):
        l = Link()
        l.unserialize(self.__dict__)

        l.href = l.href.replace("{rel}", link._rel)
        l.templated = False
        l.name = "%s:%s" % (self.name, link._rel)

        return l


class LinkContainer(object):
    def __init__(self):
        super(LinkContainer, self).__setattr__("_links", {})
        super(LinkContainer, self).__setattr__("_curies", {})

    def unserialize(self, name, obj):
        if isinstance(obj, dict):
            self._extract_from_dict(name, obj)
        elif isinstance(obj, list):
            self.unserialize_list(name, obj)
        else:
            raise TypeError(
                "'%s' is not a dict or a list" % obj.__class__.__name__
            )

    def unserialize_list(self, name, list_):
        if not list_:
            return

        if name == "curies":
            for curie_dict in list_:
                if "name" not in curie_dict:
                    raise ValueError(
                        "Cannot unserialize a CURIE that does not have a 'name'"
                    )
                if "href" not in curie_dict:
                    raise ValueError(
                        "Cannot unserialize a CURIE that does not have a 'href'"
                    )
                if "{rel}" not in curie_dict["href"]:
                    warnings.warn(
                        "CURIE named: '%s' does not include a '{rel}' template element in HREF" % curie_dict["name"]
                    )
                c = CURIE()
                c._rel = "curies"
                c.unserialize(curie_dict)

                self._curies[c.name] = c
            return

        if ":" not in name:
            for link_dict in list_:
                if "name" not in link_dict:
                    raise ValueError(
                        "Cannot unserialize a Link in a list that does not have a 'name'"
                    )
                l = Link()
                l._rel = name
                l.unserialize(link_dict)
                self._links.append(l)


        curie_name = ""
        if ":" in name:
            parts = name.split(":")
            if len(parts) != 2:
                raise ValueError(
                    "Invalid link relation curry syntax for '%s'" % name
                )
            curie_name = parts[0]
            name = parts[1]

        for link_dict in list_:
            l = Link()
            l._rel = name
            l.unserialize(obj)

            if curie_name and curie_name in self._curies:
                l._documentation = self._curies[curie_name].resolve(l)

            self._links[name] = l


    def _extract_from_dict(self, name, obj):
        if not obj:
            return

        if name == "curies":
            raise TypeError("CURIEs must be contained in a list, not a object")

        curie_name = ""
        if ":" in name:
            parts = name.split(":")
            if len(parts) != 2:
                raise ValueError(
                    "Invalid link relation curry syntax for '%s'" % name
                )
            curie_name = parts[0]
            name = parts[1]

        l = Link()
        l._rel = name
        l.unserialize(obj)

        if curie_name and curie_name in self._curies:
            l._documentation = self._curies[curie_name].resolve(l)

        self._links[name] = l

    def __getattr__(self, key):
        if key not in self._links:
            raise AttributeError(key)
        return self._links[key]

    def __str__(self):
        return "LinkContainer(" + pprint.pformat(self._links) + ")"

class ResourceContainer(object):
    def __init__(self):
        super(ResourceContainer, self).__setattr__("_resources", {})

    def __getattr__(self, key):
        if key not in self._resources:
            if _embedded_empty_list_fallback:
                return []
            raise AttributeError(key)
        return self._resources[key]

    def contains(self, key):
        return key in self

    def resource_names(self):
        return self._resources.keys()

    def __str__(self):
        return "ResourceContainer(" + pprint.pformat(self._resources) + ")"

def _def_wrapper_recursion(val):
    """ Convert dicts in the function argument into DictionaryWrapppers """
    if isinstance(val, dict):
        return DictionaryWrapper(val)
    if isinstance(val, (list, tuple)):
        return [_def_wrapper_recursion(e) for e in val]
    return val


class DictionaryWrapper(dict):
    """A dictionary whose items can be accessed using 'dot notation'.

    DictionaryWrapper is a dictionary with overloaded __getattr__ and __setattr__
    methods, allowing access to stored items using both dictionary-access
    and class-attribute dot-notation.

    For example:

        >>> foo = DictionaryWrapper({"fizz": "buzz"})
        >>> print(foo.fizz)
        buzz
        >>> print(foo["fizz"])
        buzz

    Additionally, whenever an item is set into the dict (including at initialization),
    if the value is a dictionary then it is converted into a DictionaryWrapper.
    """

    def __init__(self, dict_=None, *args, **kwargs):
        if not dict_:
            return

        if not isinstance(dict_, dict):
            raise TypeError('\'dict_\' is not a dict')

        for k, v in dict_.items():
            self[k] = v

        super(DictionaryWrapper, self).__init__(*args, **kwargs)

    def __getattr__(self, key):
        return super(DictionaryWrapper, self).__getitem__(key)

    def __setattr__(self, key, value):
        return super(DictionaryWrapper, self).__setitem__(
            key,
            _def_wrapper_recursion(value)
        )

    def __setitem__(self, key, value):
        return super(DictionaryWrapper, self).__setitem__(
            key,
            _def_wrapper_recursion(value)
        )

    def update(self, dict_):
        """ Override default `update` method to modify any dictionary values.

        Use DictionaryWrapper.__setitem__ method to update all values in the
        provided dictionary, rather than the mixed-in dict.__setitem__, because
        we need to convert all dictionaries in the provided arugment into
        DictionaryWrapper instances themselves.
        """
        if not isinstance(dict_, dict):
            raise TypeError(
                "'%s' object is not iterable" % dict_.__class__.__name__
            )
        for key, value in dict_.items():
            self[key] = value


class Resource(object):
    def __init__(self, dict_=None):
        if dict_ and not isinstance(dict_, dict):
            raise TypeError("'%s' must be a dict" % dict_.__class__.__name__)

        super(Resource, self).__setattr__("links", LinkContainer())
        super(Resource, self).__setattr__("embedded", ResourceContainer())
        super(Resource, self).__setattr__("_state", DictionaryWrapper())

        if dict_:
            self.unserialize(dict_)

    def unserialize(self, dict_):
        for key, value in dict_.items():
            if key == "_links":
                if not isinstance(value, dict):
                    raise TypeError(
                        "'%s' must be a dict" % value.__class__.__name__
                    )
                if "curies" in value:
                    self.links.unserialize("curies", value["curies"])
                    value.pop("curies", None)
                for name, obj in value.items():
                    self.links.unserialize(name, obj)
            elif key == "_embedded":
                if not isinstance(value, dict):
                    raise TypeError(
                        "'%s' must be a dict" % value.__class__.__name__
                    )
                for name, list_ in value.items():
                    self.embedded._resources[name] = [Resource(res) for res in list_]
            else:
                self._state[key] = value

    def update(self, dict_, partial=True):
        if not isinstance(dict_, dict):
            raise TypeError("'%s' must be a dict" % dict_.__class__.__name__)

        if partial:
            self._state.update(dict_)
        else:
            self._state = DictionaryWrapper(dict_)

    def __getattr__(self, key):
        if key not in self._state:
            raise AttributeError(key)
        return self._state[key]

    def __setattr__(self, key, value):
        if key not in self._state:
            raise AttributeError(key)
        self._state[key] = value

    def __str__(self):
        dict_ = {
            "links": self.links,
            "embedded": self.embedded
        }
        dict_.update(self._state)

        return "Resource(" + pprint.pformat(dict_) + ")"



def main():
    import json, pudb
    j = """
    {
        "foo": "bar",
        "fizz": "buzz",
        "_links": {
            "test": {
                "href": "/my_test"
            },
            "curies": [
                {
                    "href": "/foo/{rel}",
                    "name": "foo"
                }
            ],
            "foo:bar": {
                "href": "/bar"
            },
            "placeholder": {
                "href": "/foo/{?bar*}",
                "templated": true
            }
        }
    }

    """

    j = json.loads(j)
    r = Resource(j)
    #print(r)
    #print(r.links)
    #print(r.links.bar)
    #print(r.links.test)

    def do_req(*args, **kwargs):
        print("args", args)
        print("kwargs", kwargs)
    set_request_func(debug_request_func)

    import pudb; pu.db
    r.links.placeholder(["fizz", "buzz"])


if __name__ == "__main__":
    main()

"""
res = entrypoint(host="http://api.amberengine.dev", method="options")

listing = res.links.products.query()
if listing.total == 0:
    raise Exception()
p = listing.embedded.products[0]

p.links.self()
p.links.update()"""
