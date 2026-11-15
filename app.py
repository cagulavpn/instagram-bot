            # Trimiterea efectivă a mesajului dacă am găsit grupul
            if chat_thread:
                try:
                    message_text = messages_list[msg_index % len(messages_list)]
                    msg_index += 1
                    
                    # Trimitem mesajul
                    sent_msg = client.direct_send(message_text, thread_ids=[chat_thread.id])
                    messages_sent_in_session += 1
                    log_message(f"[{bot_name}] 🎯 Lovitură reușită pe '{target_group}' (Total cont: {messages_sent_in_session})")
                    
                    # Autoreact robust
                    if emoji_choice:
                        try:
                            msg_id = None
                            # Instagrapi poate returna un obiect DirectMessage, un dict sau o listă de dict-uri/obiecte
                            if isinstance(sent_msg, list) and len(sent_msg) > 0:
                                first_item = sent_msg[0]
                                msg_id = getattr(first_item, 'id', None) or (first_item.get('id') if isinstance(first_item, dict) else None)
                            elif hasattr(sent_msg, 'id'):
                                msg_id = sent_msg.id
                            elif isinstance(sent_msg, dict):
                                msg_id = sent_msg.get('id')

                            if msg_id:
                                client.direct_message_reaction(chat_thread.id, msg_id, reaction=emoji_choice)
                                log_message(f"[{bot_name}] ⭐ Autoreact aplicat: {emoji_choice}")
                            else:
                                # Fallback alternativ: preluăm ultimul mesaj trimis din thread dacă id-ul direct nu s-a putut citi
                                messages_in_chat = client.direct_messages(chat_thread.id, amount=1)
                                if messages_in_chat:
                                    last_msg_id = messages_in_chat[0].id
                                    client.direct_message_reaction(chat_thread.id, last_msg_id, reaction=emoji_choice)
                                    log_message(f"[{bot_name}] ⭐ Autoreact aplicat pe ultimul mesaj din fir: {emoji_choice}")
                        except Exception as react_err:
                            log_message(f"[{bot_name}] ⚠️ Eroare autoreact: {str(react_err)}")

                except Exception as e:
                    log_message(f"[{bot_name}] ⚠️ Eroare la trimitere: {str(e)}")
            else:
                log_message(f"[{bot_name}] ⚠️ Ținta '{target_group}' nu a fost găsită în flux.")
