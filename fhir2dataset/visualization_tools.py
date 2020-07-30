OPEN_CHAR = ["[", "{", "("]
CLOSE_CHAR = ["]", "}", ")"]
SAFE_CHAR = ["'", '"']
DEFAULT_BREAKLINE_CHAR = "\n"
DEFAULT_INDENT_CHAR = " "


def custom_repr(
    string: str,
    indent_width: int = 4,
    breakline_char: str = DEFAULT_BREAKLINE_CHAR,
    indent_char: str = DEFAULT_INDENT_CHAR,
):
    nested_int = 0
    new_string = ""
    safe_zone = False
    len_breakline_char = len(breakline_char)
    for character in string:
        if character in SAFE_CHAR:
            safe_zone = not safe_zone
            new_string += character
        elif safe_zone:
            new_string += character
        elif character in OPEN_CHAR:
            nested_int += 1
            new_string += character + breakline_char + nested_int * indent_width * indent_char
        elif character == ",":
            if new_string[-len_breakline_char:] == breakline_char:
                new_string = new_string[:-len_breakline_char]
            new_string += "," + breakline_char + (nested_int * (indent_width) - 1) * indent_char
        elif character in CLOSE_CHAR:
            nested_int -= 1
            if new_string[-len_breakline_char:] == breakline_char:
                new_string = new_string[:-len_breakline_char]
            new_string += (
                breakline_char
                + nested_int * indent_width * indent_char
                + character
                + breakline_char
            )
        else:
            new_string += character
    return new_string
