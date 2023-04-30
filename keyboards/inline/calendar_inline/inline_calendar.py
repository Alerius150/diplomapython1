import calendar
from datetime import date
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from loader import bot
from utils.logger import logger

from keyboards.inline.filter import calendar_factory, my_date, for_search


def get_next_or_prev_mont(action: str, year: int, month: int, command=None, state=None) -> InlineKeyboardMarkup:
    """
    Функция корректирует год и месяц если пользователь нажал на стрелочки выбора месяца
    :param state: На случай перелистывания календаря с основных команд
    :param command: На случай перелистывания календаря с основных команд
    :param action: След или предыдущий месяц
    :param year: год с коллбэка
    :param month: месяц оттуда же
    :return: клавиатуру с новыми данными
    """
    logger.info(' ')
    if action == 'next':
        logger.info('next month')
        if month == 12:
            logger.info('next year')
            year += 1
            month = 1
        else:
            logger.info('next month')
            month += 1
    else:
        logger.info('prev month')
        if month == 1:
            logger.info('prev year')
            year -= 1
            month = 12
        else:
            logger.info('prev month')
            month -= 1
    return bot_get_keyboard_inline(year=year, month=month) if command is None else bot_get_keyboard_inline(year, month,
                                                                                                           command,
                                                                                                           state)


def bot_get_keyboard_inline(year=None, month=None, command='calendar', state='None') -> InlineKeyboardMarkup:
    """
    Функция делает Inline клавиатуру-календарь
    :param state: На случай перелистывания календаря с основных команд
    :param command: Для формирования коллбэкДаты
    :param year: Текущий год, если не задано иное
    :param month: Текущий месяц, если не задано иное
    :return: InlineKeyboardMarkup
    """
    logger.info(' ')
    month = date.today().month if month is None else month
    year = date.today().year if year is None else year
    my_calendar = calendar.monthcalendar(year, month)
    keyboard = InlineKeyboardMarkup()
    empty_data = 'EMPTY'  # Пустая дата для месяца и дня недели

    days_of_week = [InlineKeyboardButton(day, callback_data=empty_data) for day in [
        'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'
    ]]
    keyboard.add(InlineKeyboardButton(f'{calendar.month_name[month]}', callback_data=empty_data))
    keyboard.add(*days_of_week, row_width=7)
    for week in my_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(' ', callback_data=empty_data))
            else:
                for_callback = my_date.new(year=year, month=month,
                                           day=day, ) if command == 'calendar' else for_search.new(year=year,
                                                                                                   month=month,
                                                                                                   day=day,
                                                                                                   state=state)
                row.append(InlineKeyboardButton(day, callback_data=for_callback))
        keyboard.add(*row, row_width=7)
        logger.info('create days')
    keyboard.add(
        InlineKeyboardButton('<<', callback_data=calendar_factory.new(action="prev", year=year, month=month,
                                                                      command=command, state=state)),
        InlineKeyboardButton('>>', callback_data=calendar_factory.new(action="next", year=year, month=month,
                                                                      command=command, state=state)),
    )
    logger.info('create calendar')
    return keyboard


@bot.callback_query_handler(func=None, calendar_config=calendar_factory.filter())
def callback_inline_action_prev_next(call: CallbackQuery):
    """
    Ловит выбор пользователя с календаря, если было выбрано перелистывание месяца
    :param call: Выбор пользователя
    """
    logger.info(' ')
    callback_data = calendar_factory.parse(callback_data=call.data)
    action, year, month, command, state = (
        callback_data['action'], int(callback_data['year']), int(callback_data['month']), callback_data['command'],
        callback_data['state'])
    bot.edit_message_text('Месяц', call.message.chat.id, call.message.id,
                          reply_markup=get_next_or_prev_mont(action=action, year=year,
                                                             month=month, command=command, state=state))


@bot.callback_query_handler(func=lambda call: call.data.startswith('EMPTY'))
def if_empty_callback(call: CallbackQuery):
    logger.error()
    bot.answer_callback_query(callback_query_id=call.id,
                              text='Выберите число!')

    from calendar import monthrange

    from telegram_bot_calendar.base import *

    STEPS = {YEAR: MONTH, MONTH: DAY}

    PREV_STEPS = {DAY: MONTH, MONTH: YEAR, YEAR: YEAR}
    PREV_ACTIONS = {DAY: GOTO, MONTH: GOTO, YEAR: NOTHING}

    class DetailedTelegramCalendar(TelegramCalendar):
        first_step = YEAR

        def __init__(self, calendar_id=0, current_date=None, additional_buttons=None, locale='en',
                     min_date=None,
                     max_date=None, telethon=False, **kwargs):
            super(DetailedTelegramCalendar, self).__init__(calendar_id, current_date=current_date,
                                                           additional_buttons=additional_buttons, locale=locale,
                                                           min_date=min_date, max_date=max_date, is_random=False,
                                                           telethon=telethon, **kwargs)

        def _build(self, step=None, **kwargs):
            if not step:
                step = self.first_step

            self.step = step
            if step == YEAR:
                self._build_years()
            elif step == MONTH:
                self._build_months()
            elif step == DAY:
                self._build_days()

        def _process(self, call_data, *args, **kwargs):
            params = call_data.split("_")
            params = dict(
                zip(["start", "calendar_id", "action", "step", "year", "month", "day"][:len(params)], params))

            if params['action'] == NOTHING:
                return None, None, None
            step = params['step']

            year = int(params['year'])
            month = int(params['month'])
            day = int(params['day'])
            self.current_date = date(year, month, day)

            if params['action'] == GOTO:
                self._build(step=step)
                return None, self._keyboard, step

            if params['action'] == SELECT:
                if step in STEPS:
                    self._build(step=STEPS[step])
                    return None, self._keyboard, STEPS[step]
                else:
                    return self.current_date, None, step

        def _build_years(self, *args, **kwargs):
            years_num = self.size_year * self.size_year_column

            start = self.current_date - relativedelta(years=(years_num - 1) // 2)
            years = self._get_period(YEAR, start, years_num)
            years_buttons = rows(
                [
                    self._build_button(d.year if d else self.empty_year_button, SELECT if d else NOTHING, YEAR, d,
                                       is_random=self.is_random)
                    for d in years
                ],
                self.size_year
            )

            nav_buttons = self._build_nav_buttons(YEAR, diff=relativedelta(years=years_num),
                                                  mind=max_date(start, YEAR),
                                                  maxd=min_date(start + relativedelta(years=years_num - 1), YEAR))

            self._keyboard = self._build_keyboard(years_buttons + nav_buttons)

        def _build_months(self, *args, **kwargs):
            start = self.current_date.replace(month=1)
            months = self._get_period(MONTH, self.current_date.replace(month=1), 12)
            months_buttons = rows(
                [
                    self._build_button(
                        self.months[self.locale][d.month - 1] if d else self.empty_month_button,  # button text
                        SELECT if d else NOTHING,  # action
                        MONTH, d, is_random=self.is_random  # other parameters
                    )
                    for d in months
                ],
                self.size_month)

            nav_buttons = self._build_nav_buttons(MONTH, diff=relativedelta(months=12),
                                                  mind=max_date(start, MONTH),
                                                  maxd=min_date(start.replace(month=12), MONTH))

            self._keyboard = self._build_keyboard(months_buttons + nav_buttons)

        def _build_days(self, *args, **kwargs):
            days_num = monthrange(self.current_date.year, self.current_date.month)[1]

            start = self.current_date.replace(day=1)
            days = self._get_period(DAY, start, days_num)

            days_buttons = rows(
                [
                    self._build_button(d.day if d else self.empty_day_button, SELECT if d else NOTHING, DAY, d,
                                       is_random=self.is_random)
                    for d in days
                ],
                self.size_day
            )

            days_of_week_buttons = [[
                self._build_button(self.days_of_week[self.locale][i], NOTHING) for i in range(7)
            ]]

            # mind and maxd are swapped since we need maximum and minimum days in the month
            # without swapping next page can generated incorrectly
            nav_buttons = self._build_nav_buttons(DAY, diff=relativedelta(months=1),
                                                  maxd=max_date(start, MONTH),
                                                  mind=min_date(start + relativedelta(days=days_num - 1), MONTH))

            self._keyboard = self._build_keyboard(days_of_week_buttons + days_buttons + nav_buttons)

        def _build_nav_buttons(self, step, diff, mind, maxd, *args, **kwargs):

            text = self.nav_buttons[step]

            sld = list(map(str, self.current_date.timetuple()[:3]))
            data = [sld[0], self.months[self.locale][int(sld[1]) - 1], sld[2]]
            data = dict(zip(["year", "month", "day"], data))
            prev_page = self.current_date - diff
            next_page = self.current_date + diff

            prev_exists = mind - relativedelta(**{LSTEP[step] + "s": 1}) >= self.min_date
            next_exists = maxd + relativedelta(**{LSTEP[step] + "s": 1}) <= self.max_date

            return [[
                self._build_button(text[0].format(**data) if prev_exists else self.empty_nav_button,
                                   GOTO if prev_exists else NOTHING, step, prev_page, is_random=self.is_random),
                self._build_button(text[1].format(**data),
                                   PREV_ACTIONS[step], PREV_STEPS[step], self.current_date, is_random=self.is_random),
                self._build_button(text[2].format(**data) if next_exists else self.empty_nav_button,
                                   GOTO if next_exists else NOTHING, step, next_page, is_random=self.is_random),
            ]]

        def _get_period(self, step, start, diff, *args, **kwargs):
            if step != DAY:
                return super(DetailedTelegramCalendar, self)._get_period(step, start, diff, *args, **kwargs)

            dates = []
            cl = calendar.monthcalendar(start.year, start.month)
            for week in cl:
                for day in week:
                    if day != 0 and self._valid_date(date(start.year, start.month, day)):
                        dates.append(date(start.year, start.month, day))
                    else:
                        dates.append(None)

            return dates

        from telebot import TeleBot
        from datetime import date

        from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP

        bot = TeleBot("5852786867")

        @bot.message_handler(commands=['start'])
        def start(m):
            calendar, step = DetailedTelegramCalendar(max_date=date.today()).build()
            bot.send_message(m.chat.id,
                             f"Выбрать {LSTEP[step]}",
                             reply_markup=calendar)

        @bot.callback_query_handler(func=DetailedTelegramCalendar.func())
        def cal(c):
            result, key, step = DetailedTelegramCalendar(max_date=date.today()).process(c.data)
            if not result and key:
                bot.edit_message_text(f"Выбрать{LSTEP[step]}",
                                      c.message.chat.id,
                                      c.message.message_id,
                                      reply_markup=key)
            elif result:
                bot.edit_message_text(f"Вы выбрали {result}",
                                      c.message.chat.id,
                                      c.message.message_id)

        bot.polling()