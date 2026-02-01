"""
FSM States for finance bot.
Handles step-by-step user interactions.
"""
from aiogram.fsm.state import State, StatesGroup


class AddTransactionStates(StatesGroup):
    """States for adding transaction flow."""
    choosing_type = State()        # Choosing income or expense
    waiting_for_input = State()    # Waiting for text or voice input
    confirming = State()           # Confirming the transaction


class AddCategoryStates(StatesGroup):
    """States for adding category flow."""
    choosing_type = State()        # Choosing income or expense category
    entering_name = State()        # Entering category name


class EditCategoryStates(StatesGroup):
    """States for editing category flow."""
    selecting_category = State()   # Selecting category to edit
    entering_new_name = State()    # Entering new name


class DeleteCategoryStates(StatesGroup):
    """States for deleting category flow."""
    selecting_category = State()   # Selecting category to delete
    confirming = State()           # Confirming deletion


class ReportsStates(StatesGroup):
    """States for reports flow."""
    choosing_month = State()       # Selecting month for report
