from unittest import mock
import unittest
import warnings

import uri_parsing


class Unpack(unittest.TestCase):
    """ Test suite for the uri_parsing.unpack function.  """

    def test_list_explode(self):
        """ Assert expected result for an unpack call with a list and explode.

        When unpack is provided with a list and explode=True, it should return
        an exact copy of the list originally provided.
        """
        value = ["fizz", "buzz"]
        explode = True

        expected = value
        self.assertEqual(uri_parsing.unpack(value, explode), expected)

    def test_list_no_explode(self):
        """ Assert expected result for an unpack call with a list but no expldoe.

        When unpack is provided with a list but explode is False, it should
        return a list containing a string of the originial list in
        comma-delimited format.
        """
        value = ["fizz", "buzz"]
        explode = False

        expected = [",".join(value)]
        self.assertEqual(uri_parsing.unpack(value, explode), expected)

    def test_dict_explode(self):
        """ Assert expected result for an unpack call with a dict and explode.

        When unpack is provided with a dictionary and explode is True, it
        should return a list containing a string in the form "key=value"

        """
        value = {"foo": "bar", "fizz": "buzz"}
        explode = True

        expected = ["foo=bar", "fizz=buzz"]
        self.assertEqual(sorted(uri_parsing.unpack(value, explode)), sorted(expected))

    def test_dict_no_explode(self):
        """ Assert expected result for an unpack call with a dicti but no explode.

        When unpack is provided with a dictionary while expode is False, it
        should return a list composed of seperate elements for each key and
        associated value in the dict.
        """
        value = {"foo": "bar", "fizz": "buzz"}
        explode = False

        expected = ["foo", "bar", "fizz", "buzz"]
        self.assertEqual(sorted(uri_parsing.unpack(value, explode)), sorted(expected))

    def test_str(self):
        """ Assert unpack returns a list containing the provided string. """
        value = "this is a test value"
        explode = False

        expected = [value]
        self.assertEqual(uri_parsing.unpack(value, explode), expected)

    def test_bool(self):
        """ Assert unpack returns a list containing the provided bool. """
        value = True
        explode = False

        expected = [value]
        self.assertEqual(uri_parsing.unpack(value, explode), expected)

    def test_int(self):
        """ Assert unpack returns a list containing the provided int. """
        value = 314159
        explode = False

        expected = [value]
        self.assertEqual(uri_parsing.unpack(value, explode), expected)


class TextLimit(unittest.TestCase):
    """ Test suite for the uri_parsing.text_limit function.  """

    def test_non_string_value(self):
        """ Assert raised error for a text_limit call with a non-str value type.

        When text_limit is provided a value argument that is not a string,
        it should raise a TypeError.
        """
        limit = 5
        value = ["this", "is", "not", "a", "string"]

        with self.assertRaises(TypeError):
            uri_parsing.text_limit(limit, value)

    def test_non_int_limit(self):
        """ Assert raised error for a text_limit call with a non-int limit type.

        When text_limit is provided a limit argument that is not an integer,
        it should raise a TypeError.
        """
        limit = {"bad": "limit"}
        value = "foobar"

        with self.assertRaises(TypeError):
            uri_parsing.text_limit(limit, value)

    def test_valid_limit_and_value(self):
        """ Assert expected result for a test_limit call with a valid limit. """
        limit = 2
        value = "fizz buzz foo bar"

        test_cases = [
            {"limit": 0, "value": value, "expect": value},
            {"limit": 2, "value": value, "expect": value[:2]},
            {"limit": 5, "value": value, "expect": value[:5]},
            {"limit": -4, "value": value, "expect": value[:-4]},
        ]

        for case in test_cases:
            self.assertEqual(
                uri_parsing.text_limit(case["limit"], case["value"]),
                case["expect"]
            )

    def test_empty_str_value(self):
        """ Assert expected result for a text_limit call with an empty str value. """
        limit = 3
        value = ""

        expected = ""
        self.assertEqual(uri_parsing.text_limit(limit, value), expected)


class ValueExtraction(unittest.TestCase):
    """ Test suite for the uri_parsing.value_extraction function.  """

    def test_empty_template(self):
        """ Assert raised error for a value_extraction call with an empty str template. """
        template = ""
        args = []
        kwargs = {}

        with self.assertRaises(ValueError):
            uri_parsing.value_extraction(template, *args, **kwargs)

    def test_missing_args_and_kwargs(self):
        """ Assert raised error for a value_extraction call which is missing required args/kwargs. """
        template = "one,two,three,four"
        args = []
        kwargs = {}

        with self.assertRaises(ValueError):
            uri_parsing.value_extraction(template, *args, **kwargs)

    def test_bad_template_format(self):
        """ Assert raised error for a value_extraction call which has a bad template format. """
        template = "one:5*"
        args = ["fizz"]
        kwargs = {}

        with self.assertRaises(ValueError):
            uri_parsing.value_extraction(template, *args, **kwargs)

    def test_explode_template_format(self):
        template = "one*"

        args = [["foo", "bar"]]
        kwargs = {}
        expected = (["foo", "bar"], (), {})
        self.assertEqual(
            uri_parsing.value_extraction(template, *args, **kwargs),
            expected
        )

        args = []
        kwargs = {"one": ["fizz", "buzz"]}
        expected = (["fizz", "buzz"], (), {})
        self.assertEqual(
            uri_parsing.value_extraction(template, *args, **kwargs),
            expected
        )

    def test_text_limit_template_format(self):
        template = "one:3"
        args = ["wat do u want?"]
        kwargs = {}

        expected = (["wat"], (), {})
        self.assertEqual(
            uri_parsing.value_extraction(template, *args, **kwargs),
            expected
        )


class KeyValueExtraction(unittest.TestCase):
    """ Test suite for the uri_parsing.value_extraction function.  """

    def test_empty_template(self):
        """ Assert raised error for a value_extraction call with an empty str template. """
        template = ""
        args = []
        kwargs = {}

        with self.assertRaises(ValueError):
            uri_parsing.key_value_extraction(template, *args, **kwargs)

    def test_missing_args_and_kwargs(self):
        """ Assert raised error for a value_extraction call which is missing required args/kwargs. """
        template = "one,two,three,four"
        args = []
        kwargs = {}

        with self.assertRaises(ValueError):
            uri_parsing.key_value_extraction(template, *args, **kwargs)

    def test_bad_template_format(self):
        """ Assert raised error for a value_extraction call which has a bad template format. """
        template = "one:5*"
        args = ["fizz"]
        kwargs = {}

        with self.assertRaises(ValueError):
            uri_parsing.key_value_extraction(template, *args, **kwargs)

    def test_explode_template_format(self):
        template = "one*"

        args = [["foo", "bar"]]
        kwargs = {}
        expected = (["one=foo", "one=bar"], (), {})
        self.assertEqual(
            uri_parsing.key_value_extraction(template, *args, **kwargs),
            expected
        )

        args = []
        kwargs = {"one": ["fizz", "buzz"]}
        expected = (["one=fizz", "one=buzz"], (), {})
        self.assertEqual(
            uri_parsing.key_value_extraction(template, *args, **kwargs),
            expected
        )

    def test_text_limit_template_format(self):
        template = "one:3"
        args = ["wat do u want?"]
        kwargs = {}

        expected = (["one=wat"], (), {})
        self.assertEqual(
            uri_parsing.key_value_extraction(template, *args, **kwargs),
            expected
        )


class TestExpanders(unittest.TestCase):
    """ Test suite for all the uri_parsing expander functions.  """

    @mock.patch("uri_parsing.value_extraction")
    def test_string_expansion(self, mock_value_extraction):
        template = "hello*"
        args = ["one", "two", "three"]
        kwargs = {}

        mock_value_extraction.return_value = (args, [], kwargs)
        expected = ",".join(args)

        self.assertEqual(
            uri_parsing.string_expansion(template, args, kwargs),
            (expected, [], {})
        )

    @mock.patch("uri_parsing.string_expansion")
    def test_fragment_expansion(self, mock_string_expansion):
        template = "hello*"
        args = ["one", "two", "three"]
        kwargs = {}

        mock_string_expansion.return_value = (args, [], kwargs)
        expected = "#%s" % ",".join(args)

        self.assertEqual(
            uri_parsing.fragment_expansion(template, args, kwargs),
            (expected, [], {})
        )

    @mock.patch("uri_parsing.value_extraction")
    def test_dot_expansion(self, mock_value_extraction):
        template = "hello*"
        args = ["one", "two", "three"]
        kwargs = {}

        mock_value_extraction.return_value = (args, [], kwargs)
        expected = ".".join(args)

        self.assertEqual(
            uri_parsing.dot_expansion(template, args, kwargs),
            (expected, [], {})
        )


    @mock.patch("uri_parsing.value_extraction")
    def test_path_expansion(self, mock_value_extraction):
        template = "hello*"
        args = ["one", "two", "three"]
        kwargs = {}

        mock_value_extraction.return_value = (args, [], kwargs)
        expected = "/%s" % ",".join(args)

        self.assertEqual(
            uri_parsing.path_segment_expansion(template, args, kwargs),
            (expected, [], {})
        )


    @mock.patch("uri_parsing.key_value_extraction")
    def test_path_expansion(self, mock_key_value_extraction):
        template = "hello*"
        args = ["one", "two", "three"]
        kwargs = {}
        k_v_pairs = ["hello=one", "hello=two", "hello=three"]


        mock_key_value_extraction.return_value = (
            k_v_pairs,
            [],
            kwargs
        )
        expected = ";%s" % ",".join(k_v_pairs)

        self.assertEqual(
            uri_parsing.path_parameter_expansion(template, args, kwargs),
            (expected, [], {})
        )


    @mock.patch("uri_parsing.key_value_extraction")
    def test_form_style_expansion(self, mock_key_value_extraction):
        template = "hello*"
        args = ["one", "two", "three"]
        kwargs = {}
        k_v_pairs = ["hello=one", "hello=two", "hello=three"]


        mock_key_value_extraction.return_value = (
            k_v_pairs,
            [],
            kwargs
        )
        expected = "?%s" % "&".join(k_v_pairs)

        self.assertEqual(
            uri_parsing.form_style_expansion(template, args, kwargs),
            (expected, [], {})
        )


    @mock.patch("uri_parsing.key_value_extraction")
    def test_form_style_continuation_expansion(self, mock_key_value_extraction):
        template = "hello*"
        args = ["one", "two", "three"]
        kwargs = {}
        k_v_pairs = ["hello=one", "hello=two", "hello=three"]


        mock_key_value_extraction.return_value = (
            k_v_pairs,
            [],
            kwargs
        )
        expected = "&%s" % "&".join(k_v_pairs)

        self.assertEqual(
            uri_parsing.form_style_continuation_expansion(template, args, kwargs),
            (expected, [], {})
        )


if __name__ == '__main__':
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        unittest.main()
