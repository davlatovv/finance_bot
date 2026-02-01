"""
Tool definitions for LLM function calling.
"""

# Tool definitions for OpenRouter API (OpenAI-compatible format)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_category",
            "description": "Создать новую категорию для доходов или расходов. Вызывай только если нет подходящей существующей категории.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Название категории (короткое, на русском). Примеры: Продукты, Транспорт, Зарплата"
                    },
                    "type": {
                        "type": "string",
                        "enum": ["income", "expense"],
                        "description": "Тип категории: income для доходов, expense для расходов"
                    }
                },
                "required": ["name", "type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_transaction",
            "description": "Записать доход или расход пользователя",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Сумма в узбекских сумах. Если не удалось определить — укажи 0"
                    },
                    "type": {
                        "type": "string",
                        "enum": ["income", "expense"],
                        "description": "Тип: income для дохода, expense для расхода"
                    },
                    "category_name": {
                        "type": "string",
                        "description": "Название категории (существующей или только что созданной)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Краткое описание транзакции"
                    }
                },
                "required": ["amount", "type", "category_name"]
            }
        }
    }
]


def get_tools() -> list[dict]:
    """Get tool definitions for LLM."""
    return TOOLS
