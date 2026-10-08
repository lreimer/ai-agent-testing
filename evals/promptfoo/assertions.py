def get_assert(output, context):
    expected = context["vars"]["expected"].split("|")
    return all(fragment.lower() in output.lower() for fragment in expected)


def used_tool(output, context):
    metadata = context.get("metadata") or (context.get("providerResponse") or {}).get("metadata", {})
    calls = metadata.get("tool_calls", [])
    return any(
        call.get("name") == "lookupConference"
        and call.get("args", {}).get("topic") == context["vars"]["topic"]
        for call in calls
    )


def admits_unknown(output, context):
    answer = output.lower().replace("’", "'")
    return any(phrase in answer for phrase in (
        "do not know", "don't know", "not available", "no information",
    ))
