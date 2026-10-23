import asyncio
import json

class MeawZikNetwork:
    """ Núcleo de Rede P2P com suporte a encerramento e desconexão de sessão """
    def __init__(self, port=50000):
        self.port = port
        self.server = None
        self.connections = []
        self.on_message_callback = None
        self.on_peer_connected_callback = None
        self.on_disconnected_callback = None  # Callback para quando a conexão cai ou o host sai
        self.expected_key = None

    def set_message_callback(self, callback):
        self.on_message_callback = callback

    def set_peer_connected_callback(self, callback):
        self.on_peer_connected_callback = callback

    def set_disconnected_callback(self, callback):
        self.on_disconnected_callback = callback

    def set_expected_key(self, key):
        self.expected_key = key

    async def iniciar_servidor(self):
        self.server = await asyncio.start_server(
            self._handle_client_connection, '0.0.0.0', self.port
        )
        print(f"[*] Servidor P2P a escutar na porta {self.port}")
        async with self.server:
            await self.server.serve_forever()

    async def _handle_client_connection(self, reader, writer):
        peer_addr = writer.get_extra_info('peername')
        print(f"[+] Nova tentativa de conexão de {peer_addr}")

        try:
            data = await reader.read(1024)
            if not data:
                writer.close()
                await writer.wait_closed()
                return

            mensagem = json.loads(data.decode('utf-8'))
            
            if mensagem.get("action") == "JOIN_SESSION":
                chave_recebida = mensagem.get("payload", {}).get("key", "").strip()
                
                if self.expected_key and chave_recebida == self.expected_key:
                    resposta = {"status": "SUCCESS", "message": "Conectado com sucesso!"}
                    writer.write(json.dumps(resposta).encode('utf-8'))
                    await writer.drain()
                    
                    self.connections.append(writer)
                    print(f"[+] Peer autenticado com sucesso: {peer_addr}")
                    
                    if self.on_peer_connected_callback:
                        self.on_peer_connected_callback(peer_addr)
                else:
                    resposta = {"status": "DENIED", "message": "Chave de acesso inválida!"}
                    writer.write(json.dumps(resposta).encode('utf-8'))
                    await writer.drain()
                    writer.close()
                    await writer.wait_closed()
                    print(f"[-] Peer rejeitado (chave incorreta): {peer_addr}")
                    return

            while True:
                data = await reader.read(1024)
                if not data:
                    break
                
                mensagem = json.loads(data.decode('utf-8'))
                if self.on_message_callback:
                    self.on_message_callback(mensagem)

        except Exception as e:
            print(f"[!] Erro na conexão com {peer_addr}: {e}")
        finally:
            if writer in self.connections:
                self.connections.remove(writer)
            writer.close()
            await writer.wait_closed()

    async def conectar_a_peer(self, host, port, chave):
        try:
            reader, writer = await asyncio.open_connection(host, port)
            
            handshake = {"action": "JOIN_SESSION", "payload": {"key": chave}}
            writer.write(json.dumps(handshake).encode('utf-8'))
            await writer.drain()

            resposta_data = await reader.read(1024)
            if not resposta_data:
                return False

            resposta = json.loads(resposta_data.decode('utf-8'))

            if resposta.get("status") == "SUCCESS":
                self.connections.append((reader, writer))
                print(f"[+] Autenticado e conectado com sucesso a {host}:{port}")
                
                asyncio.create_task(self._ouvir_loop_cliente(reader))
                return True
            else:
                writer.close()
                await writer.wait_closed()
                return False

        except Exception as e:
            print(f"[!] Falha ao conectar a {host}:{port} -> {e}")
            return False

    async def _ouvir_loop_cliente(self, reader):
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                mensagem = json.loads(data.decode('utf-8'))
                
                if mensagem.get("action") == "HOST_DISCONNECTED":
                    print("[!] O anfitrião encerrou a sessão.")
                    break

                if self.on_message_callback:
                    self.on_message_callback(mensagem)
        except Exception as e:
            print(f"[!] Erro no loop de escuta do cliente: {e}")
        finally:
            if self.on_disconnected_callback:
                self.on_disconnected_callback()

    async def enviar_comando(self, acao, payload=None):
        if payload is None:
            payload = {}
        
        mensagem = json.dumps({"action": acao, "payload": payload})
        dados = mensagem.encode('utf-8')

        for conn in list(self.connections):
            writer = conn[1] if isinstance(conn, tuple) else conn
            try:
                writer.write(dados)
                await writer.drain()
            except Exception as e:
                print(f"[!] Erro ao enviar dados para um peer: {e}")

    def fechar_todas_conexoes(self):
        """ Fecha ativamente todas as conexões ativas (usado pelo Host ao parar) """
        for conn in list(self.connections):
            try:
                writer = conn[1] if isinstance(conn, tuple) else conn
                writer.close()
            except Exception:
                pass
        self.connections.clear()