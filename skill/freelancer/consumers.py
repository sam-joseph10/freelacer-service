import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import ChatRoom, Message
from asgiref.sync import async_to_sync

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']

        # Check if user is allowed in this chat
        if self.user.is_authenticated and await self.is_user_in_room():
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            # 🟢 Send existing chat history on connection
            history = await self.get_chat_history()
            await self.send(text_data=json.dumps({
                'type': 'history',
                'messages': history
            }))
            await self.mark_as_read()
        else:
            await self.close()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_content = data.get('message', '').strip()

        if not message_content:
            return  # Ignore empty messages

        sender = self.user
        if not sender.is_authenticated:
            return

        # Save to DB and broadcast
        new_message = await self.save_message(message_content, sender.id)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': new_message['content'],
                'sender': new_message['sender'],
                'timestamp': new_message['timestamp'],
            },
        )

    async def chat_message(self, event):
        # Send new message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': event['message'],
            'sender': event['sender'],
            'timestamp': event['timestamp'],
        }))

    # ---------------- Helper DB functions ---------------- #

    @database_sync_to_async
    def is_user_in_room(self):
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            return self.user in [room.recruiter, room.freelancer]
        except ChatRoom.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, message_content, sender_id):
        sender = User.objects.get(id=sender_id)
        chat_room = ChatRoom.objects.get(id=self.room_id)

        message = Message.objects.create(
            chat_room=chat_room,
            sender=sender,
            content=message_content
        )

        # Update chat room last message
        chat_room.last_message = message_content
        chat_room.last_updated = message.timestamp

        # Update unread count
        if sender == chat_room.recruiter:
            chat_room.freelancer_unread_count += 1
        else:
            chat_room.recruiter_unread_count += 1

        chat_room.save()

        # Identify recipient
        recipient = chat_room.freelancer if sender == chat_room.recruiter else chat_room.recruiter

        # Notify recipient via their notification channel
        async_to_sync(self.channel_layer.group_send)(
            f"user_{recipient.id}_notifications",
            {
                "type": "notify_new_message",
                "room_id": chat_room.id,
                "sender": sender.username,
                "message": message.content,
                "unread_count": (
                    chat_room.freelancer_unread_count if recipient == chat_room.freelancer 
                    else chat_room.recruiter_unread_count
                ),
            }
        )

        return {
            'content': message.content,
            'sender': sender.username,
            'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }


    @database_sync_to_async
    def get_chat_history(self):
        """
        Returns the last 50 messages in this chat room.
        """
        messages = (
            Message.objects.filter(chat_room_id=self.room_id)
            .order_by("timestamp")
            .values("sender__username", "content", "timestamp")
        )
        return [
            {
                "sender": msg["sender__username"],
                "message": msg["content"],
                "timestamp": msg["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
            }
            for msg in messages
        ]

    @database_sync_to_async
    def mark_as_read(self):
        """Reset unread counter when user opens chat."""
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            if self.user == room.recruiter:
                room.recruiter_unread_count = 0
            elif self.user == room.freelancer:
                room.freelancer_unread_count = 0
            room.save()
        except ChatRoom.DoesNotExist:
            pass

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return
        
        self.group_name = f"user_{self.user.id}_notifications"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def notify_new_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'room_id': event['room_id'],
            'sender': event['sender'],
            'message': event['message'],
            'unread_count': event['unread_count'],
        }))

