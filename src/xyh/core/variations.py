from collections import OrderedDict


def variation(fn):
    def wrapper():
        return fn()

    return wrapper


def replace(
    expression_dict: OrderedDict[str, str],
    key_to_replace: str,
    key: str,
    expression: str,
):
    """
    Replace the expression in the expression_dict with the given key_to_replace
    with the new expression and key. If the key_to_replace is not found, raise a
    KeyError.
    """
    # Raise exception if key cannot be found
    if key_to_replace not in expression_dict:
        raise KeyError(f"Key '{key_to_replace}' not found in expression_dict.")

    # Get index of key to replace
    index = list(expression_dict.keys()).index(key_to_replace)

    # Insert the new key and expression at the index of the key to replace
    expression_list = list(expression_dict.items())
    expression_list[index] = (key, expression)
    expression_dict = OrderedDict(expression_list)

    return expression_dict


def append(
    expression_dict: OrderedDict[str, str],
    key: str,
    expression: str,
):
    """
    Append the new expression and key to the end of the expression_dict.

    Parameters
    ----------
    expression_dict : OrderedDict[str, str]
        The dictionary to which the new expression and key will be appended.

    key : str
        The key for the new expression.

    expression : str
        The new expression to be appended.
    """

    expression_dict[key] = expression
    return expression_dict
