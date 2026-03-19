from django.core.management.base import BaseCommand
from django.db import connections

class Command(BaseCommand):
    help = 'Sincroniza TEMP -> OFICIAL (bancos separados)'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando sincronização TEMP -> OFC...")

        try:
            with connections['default'].cursor() as cursor_temp, \
                 connections['oficial'].cursor() as cursor_ofc:

                # DEBUG bancos
                cursor_temp.execute("SELECT current_database()")
                db_temp = cursor_temp.fetchone()[0]

                cursor_ofc.execute("SELECT current_database()")
                db_ofc = cursor_ofc.fetchone()[0]

                self.stdout.write(f"📥 Lendo de: {db_temp}")
                self.stdout.write(f"📤 Gravando em: {db_ofc}")

                # =========================
                # 1. CASOS POSITIVOS
                # =========================
                cursor_temp.execute("""
                    SELECT hash_registro, local_atendimento, inicio_sintomas, notificacao, sinan, 
                           bairro, data_nasc, observacoes, resultado, aplicacao, agentes, prim_visita, situacao, geometry
                    FROM casos_positivos_temp_gl
                    WHERE geometry IS NOT NULL AND ST_IsValid(geometry)
                """)
                dados = cursor_temp.fetchall()

                if dados:
                    hashes = [d[0] for d in dados]

                    cursor_ofc.execute("""
                        DELETE FROM casos_positivos 
                        WHERE hash_registro = ANY(%s)
                    """, [hashes])

                    insert_sql = """
                        INSERT INTO casos_positivos 
                        (hash_registro, local_atendimento, inicio_sintomas, notificacao, sinan, 
                         bairro, data_nasc, observacoes, resultado, aplicacao, agentes, prim_visita, situacao, geometry)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """

                    cursor_ofc.executemany(insert_sql, dados)

                    self.stdout.write(f"✅ Casos inseridos: {len(dados)}")

                # =========================
                # 2. FOCOS
                # =========================
                cursor_temp.execute("""
                    SELECT hash_registro, n_foco, localidade, imovel, deposito, tipo_atividade, data_coleta, 
                           a_aegypti_form_aquaticas, a_aegypti_form_adultas, a_albopictus_form_aquaticas, 
                           a_albopictus_form_adultas, ovo_a_aegypti, geometry
                    FROM focos_aedes_temp
                """)
                dados = cursor_temp.fetchall()

                if dados:
                    hashes = [d[0] for d in dados]

                    cursor_ofc.execute("""
                        DELETE FROM focos_aedes 
                        WHERE hash_registro = ANY(%s)
                    """, [hashes])

                    insert_sql = """
                        INSERT INTO focos_aedes 
                        (hash_registro, n_foco, localidade, imovel, deposito, tipo_atividade, data_coleta, 
                         a_aegypti_form_aquaticas, a_aegypti_form_adultas, a_albopictus_form_aquaticas, 
                         a_albopictus_form_adultas, ovo_a_aegypti, geometry)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """

                    cursor_ofc.executemany(insert_sql, dados)
                    self.stdout.write(f"Focos inseridos: {len(dados)}")

                # =========================
                # 3. PONTOS (CORRIGIDO)
                # =========================
                cursor_temp.execute("""
                    SELECT hash_registro, numero, localidade, endereco, complemento, geometry
                    FROM pontos_estrategicos_temp
                """)
                dados = cursor_temp.fetchall()

                if dados:
                    hashes = [d[0] for d in dados]

                    cursor_ofc.execute("""
                        DELETE FROM pontos_estrategicos 
                        WHERE hash_registro = ANY(%s)
                    """, [hashes])

                    insert_sql = """
                        INSERT INTO pontos_estrategicos 
                        (hash_registro, numero, localidade, endereco, complemento, geometry)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """

                    cursor_ofc.executemany(insert_sql, dados)
                    self.stdout.write(f"Pontos inseridos: {len(dados)}")

                # =========================
                # 4. ARMADILHAS (CORRIGIDO)
                # =========================
                cursor_temp.execute("""
                    SELECT hash_registro, numero, localidade, complemento, tipo_imovel, tipo_armadilha, geometry
                    FROM relat_arm_temp
                """)
                dados = cursor_temp.fetchall()

                if dados:
                    hashes = [d[0] for d in dados]

                    cursor_ofc.execute("""
                        DELETE FROM relat_arm 
                        WHERE hash_registro = ANY(%s)
                    """, [hashes])

                    insert_sql = """
                        INSERT INTO relat_arm 
                        (hash_registro, numero, localidade, complemento, tipo_imovel, tipo_armadilha, geometry)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """

                    cursor_ofc.executemany(insert_sql, dados)
                    self.stdout.write(f"Armadilhas inseridas: {len(dados)}")

            self.stdout.write(self.style.SUCCESS("✅ SINCRONIZAÇÃO REAL CONCLUÍDA"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro: {str(e)}"))
            raise e