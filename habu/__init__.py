import pprint
import warnings

from habu import uri_parsing


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

    Calling a Link instance (like a function) will cause it to attempt to
    send a HTTP GET request to its target resource. Positional and key-word
    arguments are used to fill-in any URI template placeholders, if any exist.

    When calling a Link instance, it execute the callable `_request_func` module
    variable, which needs to be configured. See: `set_request_func`.

    A Link represents a hypermedia link from the origniating resource to a
    specified UIR. A Link instance is usually generated from parsing
    objects presented in the `_links` attribute of an
    applicaiton/HAL+JSON response.

    It contains information on how to transverse a HAL+JSON application to
    reach a specific resource.

    * `_documentation` - A Link instance generated from a CURIE template, if
    available.

    * `_rel` - Text which is either the `name` attribute of the
    current instance if the instance was unserialized from a list, or otherwise
    the key attribute which was the parent to this link during unserialization.

    * `deprecation` - An optional attribute. Any value other than `None`
    indicates that link is considered decrepet by the origniating source.

    * `href` - A string representing either a URI or a URI template,
    representing the location of a resource. Note: If it is a URI template,
    the `templated` attribute should be `True`. For more information on
    templated URIs, see: [RFC6570](https://tools.ietf.org/html/rfc6570).

    * `hreflang` - An optional attribute. It is a string used for indicating the
    langauge of the target resource.

    * `name` - An optional attribute. A string which may be used as an
    identifier when selecting other Link objects which share the same
    relation type.

    * `profile` - An optional attribute. It is a string intended for labelling
    a link with a human-readable identifier, such as those further discussed
    in [RFC5988](https://tools.ietf.org/html/rfc5988).

    * `templated` - A boolean, which when `True` indicates that the `href`
    attribute of the instance is a templated URI. If `False`, the `href`
    attribute is not templated. For more imformation on templated URIs,
    see: [RFC6570](https://tools.ietf.org/html/rfc6570).

    * `type` - An optional attribute. A string which is used to describe
    the media type expected when dereferencing the target resource.

    """
    def __init__(self):
        """ Initialize a new instance using sane defaults. """
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
        """ Call the Link to attempt to retrieve its hyperlinked resource.

        Calling a Link instance will cause it to attempt to parse its stored
        HREF. If it is templated, any positional or keyword arguments are used
        to satisfy the template.

        The HTTP GET request should be performed during the execution of the
        callable `_request_func` module variable. See `set_request_func` for
        further information.
        """
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

        # Must be a dictionary. Otherwise error.
        if not isinstance(dict_, dict):
            raise TypeError("'%s' must be a dict" % dict_.__class__.__name__)

        # A `href` attribute is required. Warning user if one is not present.
        if "href" not in dict_:
            warnings.warn("missing HREF attribute in Link")

        for key, val in dict_.items():
            if key in self.__dict__:
                self.__dict__[key] = val
            else:
                # An attribute is present in the dictionary that does not match
                # any available properties of the Link. Warn the user.
                warnings.warn("invalid Link attribute '%s' = '%s'" % (key, val))

        # If the link is decrepet, warn the user.
        # TODO: should the warning only occurr in the `__call__` instead?
        if self.deprecation:
            warnings.warn(
                "link rel '%s' has been deprecated; use at own risk" % self._rel
            )

    def __str__(self):
        """ Represent the current Link as a string. """
        return "Link(" + pprint.pformat(self.__dict__) + ")"


class CURIE(Link):
    """ Used to represent a CURIE function.

    See [8.2 Link relations](https://tools.ietf.org/html/draft-kelly-json-hal-08#section-8.2)
    for more information. Used internally for generating Link instances which
    populate the `_documentation` attribute of received Links.
    """

    def resolve(self, link):
        """ Return a new Link to documentation for the provided Link.

        Create and return a new Link instance. It is populated with a `href`
        attribute calculated from the internal `href` of the current CURIE,
        using information from the Link parameter.
        """
        l = Link()
        l.unserialize(self.__dict__)

        l.href = l.href.replace("{rel}", link._rel)
        l.templated = False
        l.name = "%s:%s" % (self.name, link._rel)

        return l


class LinkContainer(object):
    """ A in-memory container for a grouping of Link and CURIE instances.

    A storage container for Link and CURIE instances. It is usually used
    when creating a new Resource instance generated from an
    application/HAL+JSON document. It is used to as a proxy between a Resource
    and its related Links/CURIEs.

    This structure is analogous to the `_link` object present in an
    application/HAL+JSON document.
    """

    def __init__(self):
        """ Populate the instance with Link and CURIE dictionaries. """
        super(LinkContainer, self).__setattr__("_links", {})
        super(LinkContainer, self).__setattr__("_curies", {})

    def unserialize(self, name, obj):
        """ Unserializes lists or dictionaries of Link objects. """
        if isinstance(obj, dict):
            self._extract_from_dict(name, obj)
        elif isinstance(obj, list):
            self._unserialize_list(name, obj)
        else:
            raise TypeError(
                "'%s' is not a dict or a list" % obj.__class__.__name__
            )

    def _unserialize_list(self, name, list_):
        """ Internal function used to unserialize a list of Link objects. """
        if not list_:
            return # Nothing to unserialize. Just return.

        # If the type of links we have a list of are CURIEs, we need to use
        # CURIE instances instead of normal Link instances.
        if name == "curies":
            for curie_dict in list_:
                # While HAL does not require a Link document to have a `name`
                # attribute, WE do. If we have a `list` of CURIEs, the only
                # way to specify a CURIE to use is by its name.
                # TODO: Change this. Instead of inserting it as a key-value
                # entry, and thus requiring a `name` attribute, just append it
                # to a list instead. Then no `name` is required. HAL compliant.if "name" not in curie_dict:
                if "name" not in curie_dict:
                    # Must have a name. Raise an error.
                    raise ValueError(
                        "Cannot unserialize a CURIE that does not have a 'name'"
                    )

                # HAL does require all link documents to have a `href` attribute.
                # A CURIE is completely useless with a `href`, so we raise an
                # error if it does not have one.
                if "href" not in curie_dict:
                    raise ValueError(
                        "Cannot unserialize a CURIE that does not have a 'href'"
                    )

                # It is not common to have a CURIE which does not include a
                # URI template placeholder for `rel`. Warning the user
                # if one is not present.
                if "{rel}" not in curie_dict["href"]:
                    warnings.warn(
                        "CURIE named: '%s' does not include a '{rel}' template element in HREF" % curie_dict["name"]
                    )

                c = CURIE()
                c._rel = "curies"
                c.unserialize(curie_dict)

                self._curies[c.name] = c
            return # nothing else to do. Return from the method.

        # First, check if we have a CURIE specified in the name of the type
        # of links we are dealing with.
        if ":" not in name:
            # Okay, no CURIE.
            for link_dict in list_:

                """
                We are going to break convention from HAL. We REQUIRE all link
                documents to include a `name` attribute if they exist in a list.
                We require this because we need some identifier for each link
                in order to store it in the internal `_links` dictionary.
                """
                # TODO: Change this. Instead of inserting it as a key-value
                # entry, and thus requiring a `name` attribute, just append it
                # to a list instead. Then no `name` is required. HAL compliant.
                if "name" not in link_dict:
                    raise ValueError(
                        "Cannot unserialize a Link in a list that does not have a 'name'"
                    )
                l = Link()
                l._rel = name
                l.unserialize(link_dict)
                self._links.append(l)
            return # returning since we are done.

        # If we get here, we MUST have a CURIE identifier in the name.
        # Create the Link like normal, but also generate a documentation Link
        # instance for it.
        curie_name = ""
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
        """ Internal function used to unserialize a dict of Link objects. """
        if not obj:
            return # Nothing to unserialize. Just return.

        # HAL "highly recommends" only providing CURIEs in a list, rather than
        # an object. See [8.2 Link relations](https://tools.ietf.org/html/draft-kelly-json-hal-08#section-8.2)
        # for more info.
        if name == "curies":
            raise TypeError("CURIEs must be contained in a list, not a object")

        # First, check if we have a CURIE specified in the name of the type
        # of links we are dealing with.
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
        """ Allow for retrieving Link instances using property-access. """
        if key not in self._links:
            raise AttributeError(key)
        return self._links[key]

    def __str__(self):
        """ Represent the current LinkContainer as a string. """
        return "LinkContainer(" + pprint.pformat(self._links) + ")"

class ResourceContainer(object):
    """ A in-memory container for a grouping of Resource instances.

    A storage container for Resource instances. It is usually generated to
    store embedded resources from an application/HAL+JSON document. These
    resources are found under the `_embedded` attribute. This class  acts as
    a proxy between a Resource and its embedded Resources.

    This structure is analogous to the `_embedded` object present in an
    application/HAL+JSON document.
    """

    def __init__(self):
        """ Populate the instance with a Resource dictionary. """
        super(ResourceContainer, self).__setattr__("_resources", {})

    def __getattr__(self, key):
        """ Allow for retrieving Resource instances using property-access. """
        if key not in self._resources:
            # If a specified type of resource cannot be found, what do we do?
            # If `_embedded_empty_list_fallback` is `True`, return an empty
            # list. Otherwise, raise an AttributeError.
            if _embedded_empty_list_fallback:
                return []
            raise AttributeError(key)
        return self._resources[key]

    def contains(self, key):
        """ Return bool indicating if key exists in current instance. """
        return key in self

    def resource_names(self):
        """ Return a list of all available resource types. """
        return self._resources.keys()

    def __str__(self):
        """ Represent the current ResourceContainer as a string. """
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
    """ A representation of a HAL+JSON resource document.

    A Resource is a combination of links, its own state, and any related
    resources embedded in it.

    A Resource instance's state is a `DictionaryWrapper`, whose data can be
    accessed and manipulated using normal property getting/setting.

    Access to the DictionaryWrapper directly can be done via the `_state`
    property on a Resource instance.

    Any links are stored in the `links` attribute, which is a `LinkContainer`.
    Any embedded resources are stored in the `embedded` attribute, which is
    a `ResourceContainer`.
    """


    def __init__(self, dict_=None):
        """ Initialize the current instance and its attributes. """
        if dict_ and not isinstance(dict_, dict):
            raise TypeError("'%s' must be a dict" % dict_.__class__.__name__)

        super(Resource, self).__setattr__("links", LinkContainer())
        super(Resource, self).__setattr__("embedded", ResourceContainer())
        super(Resource, self).__setattr__("_state", DictionaryWrapper())

        if dict_:
            self.unserialize(dict_)

    def unserialize(self, dict_):
        """ Unserialize a dictionary into the current Resource. """
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
        """ Update the internal state of the Resource using a dictionary.

        Provide a dictionary of key-value pairs to update attributes on the
        state of the current resource.

        By default, this is a partial update. Fields not overriden in the
        `dict_` parameter remain their original values.
        Setting the `partial` parameter to `False` will completely reset
        the state to totally match the dictionary parameter.
        """
        if not isinstance(dict_, dict):
            raise TypeError("'%s' must be a dict" % dict_.__class__.__name__)

        if partial:
            self._state.update(dict_)
        else:
            self._state = DictionaryWrapper(dict_)

    def __getattr__(self, key):
        """ Get a attribute from the internal state. """
        if key not in self._state:
            raise AttributeError(key)
        return self._state[key]

    def __setattr__(self, key, value):
        """ Set an attribute on the internal state. """
        if key not in self._state:
            raise AttributeError(key)
        self._state[key] = value

    def __str__(self):
        """ Represent the current Resource as a string. """
        dict_ = {
            "links": self.links,
            "embedded": self.embedded
        }
        dict_.update(self._state)

        return "Resource(" + pprint.pformat(dict_) + ")"



def enter(uri):
    result = _request_func(uri)
    link_container = LinkContainer()
    if "_links" in result:
        for key, val in result["_links"].items():
            link_container.unserialize(key, val)
    return link_container

"""
res = entrypoint(host="http://api.amberengine.dev", method="options")

listing = res.links.products.query()
if listing.total == 0:
    raise Exception()
p = listing.embedded.products[0]

p.links.self()
p.links.update()"""
