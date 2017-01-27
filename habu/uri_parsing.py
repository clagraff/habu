import re
import warnings


def unpack(value, explode=False):
    return_list = []

    if isinstance(value, list):
        if explode:
            return_list += value
        else:
            return_list.append(",".join(value))
    elif isinstance(value, dict):
        if explode:
            for key, val in value.items():
                return_list.append("%s=%s" % (key, val))
        else:
            for key, val in value.items():
                return_list += [key, val]
    else:
        return_list.append(value)
    return return_list


def text_limit(limit, value):
    if not isinstance(value, str):
        raise TypeError("'%s' must be a string" % value.__class__.__name__)
    if limit and limit > 0:
        return value[:limit]
    return value


def value_extraction(template, *args, **kwargs):
    values = []

    placeholders = template.split(",")

    if not args and not kwargs:
        if placeholders:
            raise ValueError("missing uri placeholder data for placeholders: '%s'" % placeholders)
        return ("", args, kwargs)


    remaining_placeholders = placeholders
    for placeholder in placeholders:
        original = placeholder
        has_explode = placeholder[-1] == "*"
        has_limiter = ":" in placeholder

        if has_explode and has_limiter:
            raise ValueError("malformed uri placeholder '%s'" % placeholder)

        if has_explode:
            placeholder = placeholder[:-1]

        if has_limiter:
            parts = placeholder.split(":")
            placeholder = parts[0]
            amount = int(parts[1])
            if args and args[0] is not None:
                values.append(text_limit(amount, args[0]))
                args = tuple(a for a in args if a != args[0])
                remaining_placeholders.remove(original)
            elif placeholder in kwargs.keys() and kwargs[placeholder] is not None:
                values.append(text_limit(amount, kwargs[placeholder]))
                kwargs.pop(placeholder, None)
                remaining_placeholders.remove(original)
            continue

        if args and args[0] is not None:
            values += unpack(args[0], explode=has_explode)
            args = tuple(a for a in args if a != args[0])
            remaining_placeholders.remove(original)
        elif placeholder in kwargs.keys() and kwargs[placeholder] is not None:
            values += unpack(kwargs[placeholder], explode=has_explode)
            kwargs.pop(placeholder, None)
            remaining_placeholders.remove(original)
        continue

    if placeholders:
        warnings.warn(
            "uri placeholders '%s' remaining after parsing uri" % placeholders
        )
    return (values, args, kwargs)


def key_value_extraction(template, *args, **kwargs):
    values = []

    if not args and not kwargs:
        return ("", args, kwargs)

    placeholders = template.split(",")

    remaining_placeholders = placeholders
    for placeholder in placeholders:
        original = placeholder
        has_explode = placeholder[-1] == "*"
        has_limiter = ":" in placeholder

        if has_explode and has_limiter:
            raise ValueError("malformed uri placeholder '%s'" % placeholder)

        if has_explode:
            placeholder = placeholder[:-1]

        if has_limiter:
            parts = placeholder.split(":")
            placeholder = parts[0]
            amount = int(parts[1])
            if args and args[0] is not None:
                values.append("%s=%s" % (placeholder, text_limit(amount, args[0])))
                args = tuple(a for a in args if a != args[0])
                remaining_placeholders.remove(original)
            elif placeholder in kwargs.keys() and kwargs[placeholder] is not None:
                values.append("%s=%s" % (placeholder, text_limit(amount, kwargs[placeholder])))
                kwargs.pop(placeholder, None)
                remaining_placeholders.remove(original)
            continue

        if args and args[0] is not None:
            for item in unpack(args[0], explode=has_explode):
                values.append("%s=%s" % (placeholder, item))
            args = tuple(a for a in args if a != args[0])
            remaining_placeholders.remove(original)
        elif placeholder in kwargs.keys() and kwargs[placeholder] is not None:
            for item in unpack(kwargs[placeholder], explode=has_explode):
                values.append("%s=%s" % (placeholder, item))
            kwargs.pop(placeholder, None)
            remaining_placeholders.remove(original)
        continue

    if remaining_placeholders:
        warnings.warn(
            "uri placeholders '%s' remaining after parsing uri" % remaining_placeholders
        )
    return (values, args, kwargs)


def string_expansion(template, *args, **kwargs):
    (values, args, kwargs) = value_extraction(template, *args, **kwargs)
    return (",".join(values), args, kwargs)


def fragment_expansion(template, *args, **kwargs):
    (value, args, kwargs) = string_expansion(template, *args, **kwargs)
    return ("#%s" % ",".join(value), args, kwargs)


def dot_expansion(template, *args, **kwargs):
    (values, args, kwargs) = value_extraction(template, *args, **kwargs)
    return (".".join(values), args, kwargs)


def path_segment_expansion(template, *args, **kwargs):
    (values, args, kwargs) = value_extraction(template, *args, **kwargs)
    return ("/%s" % ",".join(values), args, kwargs)


def path_parameter_expansion(template, *args, **kwargs):
    (values, args, kwargs) = key_value_extraction(template, *args, **kwargs)
    for index, value in enumerate(values):
        parts = value.split("=")
        if not len(parts[1]):
            values[index] = parts[0]

    return (";%s" % ",".join(values), args, kwargs)


def form_style_expansion(template, *args, **kwargs):
    (values, args, kwargs) = key_value_extraction(template, *args, **kwargs)
    return ("?%s" % "&".join(values), args, kwargs)


def form_style_continuation(template, *args, **kwargs):
    (values, args, kwargs) = key_value_extraction(template, *args, **kwargs)
    return ("&%s" % "&".join(values), args, kwargs)




default_prefix_expander = string_expansion
prefix_types = {
    "+": string_expansion,
    "#": fragment_expansion,
    ".": dot_expansion,
    "/": path_segment_expansion,
    ";": path_parameter_expansion,
    "?": form_style_expansion,
    "&": form_style_continuation
}

def expand_placeholder(placeholder, *args, **kwargs):
    expander = default_prefix_expander
    if placeholder[0] in prefix_types:
        expander = prefix_types[placeholder[0]]
        placeholder = placeholder[1:]

    return expander(placeholder, *args, **kwargs)


def parse_uri(href, *args, **kwargs):
    if "{" not in href or "}" not in href:
        warnings.warn(
            "tempalted href value '%s' does not contain template placeholders"
        )
        return (href, args, kwargs)

    placeholder_regex = re.compile(r'{([^}]+)}') # example match: /foo{bar}

    # Process required positional arguments first
    placeholders = placeholder_regex.findall(href)
    for placeholder in placeholders:
        (replacement, a, kw) = expand_placeholder(placeholder, *args, **kwargs)
        args = a
        kwargs= kw

        href = href.replace("{%s}" % placeholder, replacement)

    return (href, args, kwargs)


