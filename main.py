import logging
from telegram import Update, ForceReply, Location
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import json
import os.path
import random
import datetime

ADMIN_ID = 1234
OFFSET = 0.0005
POIS = [(56.237029, 36.828190), (56.235609, 36.823130), (56.210476, 36.864926), (56.211829, 36.881902), (56.207480, 36.889232), (56.219707, 36.871182), (56.226676, 36.866620), (56.222997, 36.882375), (56.225472, 36.880723), (56.226637, 36.871834), (56.232990, 36.849507), (56.229876, 36.857499), (56.212827, 36.860407), (56.235633, 36.836388)]
entries = {}
messages = []
route_plan = []
route_log = []
locked = True
last_location_event = 0

# Enable logging
logging.basicConfig(
	format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def in_zone(what, where) -> bool:
	return (what[0] >= where[0] - OFFSET) and (what[0] <= where[0] + OFFSET) and (what[1] >= where[1] - OFFSET) and (what[1] <= where[1] + OFFSET)

def restore_messages() -> bool:
	global messages
	if os.path.isfile("messages.json"):
		with open("messages.json", "r") as file:
			messages = json.load(file)
		return True
	else:
		return False

def start(update: Update, context: CallbackContext) -> None:
	user = update.effective_user
	update.message.reply_text(
		f"Hey {user.first_name}!"
	)

def log(update: Update, context: CallbackContext) -> None:
	global entries
	user_id = update.effective_user.id
	if False: #user_id == ADMIN_ID:
		update.message.reply_text("Non-admin command!")
		return
	if locked:
		update.message.reply_text("Sorry!")
	else:
		entries[user_id] = "log"
		update.message.reply_text("Send your message! (4096 chars MAX!)")

def lock(update: Update, context: CallbackContext) -> None:
	global locked
	user_id = update.effective_user.id
	if False: #user_id == ADMIN_ID:
		update.message.reply_text("Non-admin command!")
		return
	locked = True
	update.message.reply_text("Locked messages!")

def unlock(update: Update, context: CallbackContext) -> None:
	global locked
	user_id = update.effective_user.id
	if False: #user_id == ADMIN_ID:
		update.message.reply_text("Non-admin command!")
		return
	locked = False
	update.message.reply_text("Unlocked messages!")

def restore(update: Update, context: CallbackContext) -> None:
	user_id = update.effective_user.id
	if user_id != ADMIN_ID:
		update.message.reply_text("Admin-only command!")
		return
	if not restore_messages():
		update.message.reply_text("Found no records!")
		return
	update.message.reply_text("Restored!")

def peek(update: Update, context: CallbackContext) -> None:
	user_id = update.effective_user.id
	if user_id != ADMIN_ID:
		update.message.reply_text("Admin-only command!")
		return
	s = f"Messages total: {len(messages)}"
	for i in range(0, len(messages)):
		s += f"\n{i + 1}: {len(messages[i])}"
	update.message.reply_text(s)

def dump(update: Update, context: CallbackContext) -> None:
	user_id = update.effective_user.id
	if user_id != ADMIN_ID:
		update.message.reply_text("Admin-only command!")
		return
	update.message.reply_text("ARE YOU SURE?! y/n")
	entries[user_id] = "dump"

def cancel(update: Update, context: CallbackContext) -> None:
	entries.pop(update.effective_user.id, None)
	update.message.reply_text("Whatever!")

def text(update: Update, context: CallbackContext) -> None:
	global entries, messages
	user = update.effective_user
	if user.id in entries:
		if entries[user.id] == "log":
			messages.append(f"{user.first_name}: {update.message.text}")
			with open("messages.json", "w") as file:
				json.dump(messages, file)
			update.message.reply_text("Recorded! thx")
			del entries[user.id]
			return
		if entries[user.id] == "dump":
			if update.message.text == "y":
				for i in messages:
					update.message.reply_text(i)
			else:
				update.message.reply_text("Stay alert!")
			del entries[user.id]
			return
	update.message.reply_text("What?!")

def build(update: Update, context: CallbackContext) -> None:
	global route_plan
	user_id = update.effective_user.id
	if user_id != ADMIN_ID:
		update.message.reply_text("Admin-only command!")
		return
	if len(POIS) < len(messages):
		update.message.reply_text("Not enough POIs!")
		return
	sampled = random.sample(POIS, len(messages))
	route_plan = sampled
	random.shuffle(sampled)
	for i in sampled:
		update.message.reply_location(i[0], i[1])

def route(update: Update, context: CallbackContext) -> None:
	user_id = update.effective_user.id
	if user_id != ADMIN_ID:
		update.message.reply_text("Admin-only command!")
		return
	if route_log == []:
		update.message.reply_text("No route logged!")
		return
	s = ""
	for i in route_log:
		s += f"{i[0]} — {i[1][0]},{i[1][1]} "
	update.message.reply_text(s)

def location(update: Update, context: CallbackContext) -> None:
	global last_location_event
	user_id = update.effective_user.id
	if user_id != ADMIN_ID:
		update.message.reply_text("Admin-only feature!")
		return
	if route_plan == []:
		update.message.reply_text("No route built!")
		return
	now = round(datetime.datetime.now().timestamp())
	if last_location_event + 15 > now:
		return
	message = None
	if update.edited_message:
		message = update.edited_message
	else:
		message = update.message
	if message.location.live_period is None:
		update.message.reply_text("Not a live location!")
		return
	pos = (message.location.latitude, message.location.longitude)
	for i in range(0, len(route_plan)):
		if in_zone(pos, route_plan[i]):
			update.message.reply_text(messages[i])
			del route_plan[i]
			del messages[i]
			route_log.append((datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pos))
			break
	last_location_event = now

def main() -> None:
	restore_messages()
	updater = Updater("TOKEN")

	dispatcher = updater.dispatcher

	dispatcher.add_handler(CommandHandler("start", start))
	dispatcher.add_handler(CommandHandler("log", log))
	dispatcher.add_handler(CommandHandler("restore", restore))
	dispatcher.add_handler(CommandHandler("peek", peek))
	dispatcher.add_handler(CommandHandler("dump", dump))
	dispatcher.add_handler(CommandHandler("lock", lock))
	dispatcher.add_handler(CommandHandler("unlock", unlock))
	dispatcher.add_handler(CommandHandler("build", build))
	dispatcher.add_handler(CommandHandler("cancel", cancel))
	dispatcher.add_handler(CommandHandler("route", route))

	dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, text))

	dispatcher.add_handler(MessageHandler(Filters.location, location))

	updater.start_polling()
	updater.idle()

if __name__ == "__main__":
	main()
