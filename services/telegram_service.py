import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from aiogram import Bot
from aiogram.types import ChatMemberLeft, ChatMemberKicked, InlineKeyboardMarkup

from config.settings import TELEGRAM_BOT_TOKEN, CHANNEL_ID, INVITE_LINK_EXPIRE_HOURS

logger = logging.getLogger(__name__)


class TelegramService:
    """Сервис для работы с Telegram API"""
    
    def __init__(self, bot: Bot = None):
        self.bot = bot or Bot(token=TELEGRAM_BOT_TOKEN)
        self.channel_id = CHANNEL_ID
    
    async def create_invite_link(
        self, 
        user_id: int, 
        expire_hours: int = INVITE_LINK_EXPIRE_HOURS,
        member_limit: int = 1
    ) -> Optional[str]:
        """
        Создать инвайт-ссылку для пользователя
        
        Args:
            user_id: ID пользователя (для логирования)
            expire_hours: Время жизни ссылки в часах
            member_limit: Лимит участников (по умолчанию 1)
            
        Returns:
            Инвайт-ссылка или None при ошибке
        """
        try:
            expire_date = datetime.now() + timedelta(hours=expire_hours)
            
            invite_link = await self.bot.create_chat_invite_link(
                chat_id=self.channel_id,
                member_limit=member_limit,
                expire_date=expire_date,
                name=f"User {user_id}"
            )
            
            logger.info(f"Создана инвайт-ссылка для пользователя {user_id}")
            return invite_link.invite_link
            
        except Exception as e:
            logger.error(f"Ошибка создания инвайт-ссылки для {user_id}: {e}")
            return None
    
    async def kick_user_from_channel(self, user_id: int) -> bool:
        """
        Исключить пользователя из канала
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если успешно, False если ошибка
        """
        try:
            # Банируем пользователя
            await self.bot.ban_chat_member(
                chat_id=self.channel_id,
                user_id=user_id
            )
            
            # Сразу разбаниваем, чтобы мог зайти снова после оплаты
            await self.bot.unban_chat_member(
                chat_id=self.channel_id,
                user_id=user_id
            )
            
            logger.info(f"Пользователь {user_id} исключен из канала")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка исключения пользователя {user_id}: {e}")
            return False
    
    async def check_user_in_channel(self, user_id: int) -> bool:
        """
        Проверить, находится ли пользователь в канале
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если пользователь в канале, False если нет
        """
        try:
            member = await self.bot.get_chat_member(
                chat_id=self.channel_id,
                user_id=user_id
            )
            
            # Пользователь в канале, если он не покинул и не забанен
            return not isinstance(member, (ChatMemberLeft, ChatMemberKicked))
            
        except Exception as e:
            logger.error(f"Ошибка проверки пользователя {user_id} в канале: {e}")
            return False
    
    async def send_message(
        self, 
        user_id: int, 
        text: str, 
        reply_markup: InlineKeyboardMarkup = None,
        parse_mode: str = "HTML"
    ) -> bool:
        """
        Отправить сообщение пользователю
        
        Args:
            user_id: ID пользователя
            text: Текст сообщения
            reply_markup: Клавиатура
            parse_mode: Режим парсинга (HTML/Markdown)
            
        Returns:
            True если отправлено, False если ошибка
        """
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
            return False
    
    async def send_message_to_channel(
        self, 
        text: str, 
        reply_markup: InlineKeyboardMarkup = None
    ) -> bool:
        """
        Отправить сообщение в канал
        
        Args:
            text: Текст сообщения
            reply_markup: Клавиатура
            
        Returns:
            True если отправлено, False если ошибка
        """
        try:
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения в канал: {e}")
            return False
    
    async def get_channel_info(self) -> Optional[dict]:
        """
        Получить информацию о канале
        
        Returns:
            Словарь с информацией о канале или None
        """
        try:
            chat = await self.bot.get_chat(self.channel_id)
            
            return {
                "id": chat.id,
                "title": chat.title,
                "username": chat.username,
                "description": chat.description,
                "member_count": await self.bot.get_chat_member_count(self.channel_id)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о канале: {e}")
            return None
    
    async def get_channel_member_count(self) -> int:
        """
        Получить количество участников канала
        
        Returns:
            Количество участников или 0 при ошибке
        """
        try:
            return await self.bot.get_chat_member_count(self.channel_id)
        except Exception as e:
            logger.error(f"Ошибка получения количества участников: {e}")
            return 0
    
    async def broadcast_message(
        self, 
        user_ids: List[int], 
        text: str, 
        reply_markup: InlineKeyboardMarkup = None
    ) -> dict:
        """
        Рассылка сообщения списку пользователей
        
        Args:
            user_ids: Список ID пользователей
            text: Текст сообщения
            reply_markup: Клавиатура
            
        Returns:
            Словарь со статистикой рассылки
        """
        sent = 0
        failed = 0
        blocked = 0
        
        for user_id in user_ids:
            try:
                await self.bot.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                sent += 1
                
            except Exception as e:
                error_str = str(e).lower()
                if "blocked" in error_str or "deactivated" in error_str:
                    blocked += 1
                else:
                    failed += 1
                
                logger.warning(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
        
        result = {
            "total": len(user_ids),
            "sent": sent,
            "failed": failed,
            "blocked": blocked
        }
        
        logger.info(f"Рассылка завершена: {result}")
        return result
    
    async def revoke_invite_link(self, invite_link: str) -> bool:
        """
        Отозвать инвайт-ссылку
        
        Args:
            invite_link: Ссылка для отзыва
            
        Returns:
            True если отозвана, False если ошибка
        """
        try:
            await self.bot.revoke_chat_invite_link(
                chat_id=self.channel_id,
                invite_link=invite_link
            )
            logger.info(f"Инвайт-ссылка отозвана: {invite_link}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отзыва инвайт-ссылки: {e}")
            return False
    
    async def get_bot_info(self) -> Optional[dict]:
        """
        Получить информацию о боте
        
        Returns:
            Словарь с информацией о боте
        """
        try:
            bot_info = await self.bot.get_me()
            return {
                "id": bot_info.id,
                "username": bot_info.username,
                "first_name": bot_info.first_name,
                "can_join_groups": bot_info.can_join_groups,
                "can_read_all_group_messages": bot_info.can_read_all_group_messages,
                "supports_inline_queries": bot_info.supports_inline_queries
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о боте: {e}")
            return None


# Глобальный экземпляр сервиса
telegram_service = None

def init_telegram_service(bot: Bot):
    """Инициализация сервиса с ботом"""
    global telegram_service
    telegram_service = TelegramService(bot)