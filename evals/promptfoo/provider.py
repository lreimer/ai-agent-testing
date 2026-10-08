from evals.adk_client import ask


def call_api(prompt, options, context):
    app = context["vars"]["app"]
    result = ask(app, prompt)
    return {
        "output": result["answer"],
        "metadata": {"tool_calls": result["tool_calls"], "contexts": result["contexts"]},
    }
