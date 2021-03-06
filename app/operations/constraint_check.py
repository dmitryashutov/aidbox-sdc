import json

from aiohttp import web
from app.sdk import sdk
from fhirpathpy import evaluate as fhirpath

from .utils import load_source_queries, parameter_to_env


class OperationOutcome(web.HTTPError):
    # TODO: use from aidbox-python-sdk
    status_code = 400

    def __init__(self, *, reason):
        web.HTTPError.__init__(
            self,
            text=json.dumps(
                {
                    "resourceType": "OperationOutcome",
                    # "status": 400,
                    "issue": [
                        {"severity": "error", "code": "invalid", "diagnostics": reason or "Error",}
                    ],
                    "text": {"status": "generated", "div": reason or "Something went wrong",},
                }
            ),
            content_type="application/json",
        )


@sdk.operation(["POST"], ["QuestionnaireResponse", "$constraint-check"])
async def constraint_check_operation(operation, request):
    env = parameter_to_env(request["resource"])
    questionnaire = env["Questionnaire"]
    questionnaire_response = env["QuestionnaireResponse"]
    await load_source_queries(sdk, questionnaire, env)
    errors = []
    await constraint_check(errors, questionnaire, env)
    if len(errors) > 0:
        raise OperationOutcome(reason="constraint check failure")
    return web.json_response(questionnaire_response)


async def constraint_check(errors, questionnaire_item, env):
    for constraint in questionnaire_item.get("constraint", []):
        expression = constraint["expression"]["expression"]
        result = fhirpath({}, expression, env)
        import logging

        logging.debug("expression %s", expression)
        logging.debug("result %s", result)
        logging.debug("env %s", env)

        if result == [True]:
            errors.append(constraint["human"])

    for item in questionnaire_item.get("item", []):
        await constraint_check(errors, item, env)
