def add_numbers(mappings):
    for map_ in set(mappings.values()):
        duplicates = list(filter(lambda mapping: mappings[mapping] == map_, mappings))
        if len(duplicates) > 1:
            for number, duplicate in enumerate(duplicates, 1):
                mappings[duplicate] += str(number)

    return mappings


def create_bins(buckets, foo=None):
    initial_length = len(buckets.get(""))

    for i in range(3):
        for bucket, contents in buckets.copy().items():
            if len(contents) > 1:
                which_letter_now = len(bucket)

                for content in contents:
                    content = str(content)
                    current_letter = content[: which_letter_now + 1]

                    if current_letter != bucket:
                        if not buckets.get(current_letter):
                            buckets[current_letter] = []

                        buckets[current_letter].append(content)

                current_bucket = buckets.pop(bucket)

                if bucket in current_bucket:
                    buckets[bucket] = [bucket]

        if initial_length == len(buckets):
            break

    return buckets


def create_buckets(what_collection, fields=None):
    field_bins = []

    for field in fields:
        field_bins.append(create_bins({"": list({getattr(item, field) for item in what_collection})}))

    mappings = {}

    for item in what_collection:
        mappings[item.item_id] = "".join(
            mapping_from_bins(bin_, getattr(item, field)) for bin_, field in zip(field_bins, fields)
        )

    return add_numbers(mappings)


def create_single_bucket(list_of_fields):
    field_bins = create_bins({"": list_of_fields})
    mappings = {field: mapping_from_bins(field_bins, field) for field in list_of_fields}

    numbered_mappings = add_numbers(mappings)

    return trim_mappings(numbered_mappings)


def generate_name(klass, dictionary):
    return "".join([dictionary[param] for param in klass.prompt_params])


def mapping_from_bins(bins, target):
    for mapping, items in bins.items():
        if str(target) in items:
            return mapping


def remove_duplicates(list_of_items):
    result = []
    for item in list_of_items:
        if item not in result:
            result.append(item)

    return result


def trim_mappings(mappings):
    """Sometimes mappings can be longer than necessary."""
    shortest_mapping = min(len(mapping) for mapping in mappings.values())

    if shortest_mapping > 1 and len(set(mapping[0:1] for mapping in mappings.values())) == 1:
        mappings = {k: v[1:] for k, v in mappings.items()}
        mappings = trim_mappings(mappings)

    return mappings
