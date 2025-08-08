import os
import pandas as pd
import sqlalchemy
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Float, Integer, String, UniqueConstraint, create_engine
from sqlalchemy.dialects.sqlite import insert

from FAIRS.app.constants import DATA_PATH, SOURCE_PATH, INFERENCE_PATH
from FAIRS.app.logger import logger

Base = declarative_base()


###############################################################################
class RouletteSeries(Base):
    __tablename__ = 'ROULETTE_SERIES'
    id = Column(Integer, primary_key=True)
    extraction = Column(Integer)
    color = Column(String) 
    color_code = Column(Integer)
    position = Column(Integer)
    __table_args__ = (
        UniqueConstraint('id'),
    )
   


###############################################################################
class PredictedGames(Base):
    __tablename__ = 'PREDICTED_GAMES'
    id = Column(Integer, primary_key=True)
    checkpoint = Column(String, primary_key=True)
    extraction = Column(Integer)
    color = Column(String)
    action = Column(String)     
    __table_args__ = (
        UniqueConstraint('id', 'checkpoint'),
    )
   

###############################################################################
class CheckpointSummary(Base):
    __tablename__ = 'CHECKPOINTS_SUMMARY'    
    checkpoint = Column(String, primary_key=True)
    sample_size = Column(Float)
    seed = Column(Integer)
    precision = Column(Integer)
    episodes = Column(Integer)
    max_steps_episode = Column(Integer)
    batch_size = Column(Integer)
    jit_compile = Column(String)
    has_tensorboard_logs = Column(String)
    learning_rate = Column(Float)
    neurons = Column(Integer)
    embedding_dimensions = Column(Integer)
    perceptive_field_size = Column(Integer)
    exploration_rate = Column(Float)
    exploration_rate_decay = Column(Float)
    discount_rate = Column(Float)
    model_update_frequency = Column(Integer)
    loss = Column(Float)
    accuracy = Column(Float)   
    __table_args__ = (
        UniqueConstraint('checkpoint'),
    )


# [DATABASE]
###############################################################################
class FAIRSDatabase:

    def __init__(self):             
        self.db_path = os.path.join(DATA_PATH, 'FAIRS_database.db')
        self.source_path = os.path.join(SOURCE_PATH, 'FAIRS_dataset.csv')
        self.engine = create_engine(f'sqlite:///{self.db_path}', echo=False, future=True)
        self.Session = sessionmaker(bind=self.engine, future=True)
        self.insert_batch_size = 2000

    #--------------------------------------------------------------------------       
    def initialize_database(self):
        Base.metadata.create_all(self.engine)  

    #--------------------------------------------------------------------------       
    def update_database_from_source(self): 
        dataset = pd.read_csv(self.source_path, sep=';', encoding='utf-8')                 
        self.save_roulette_data(dataset)

        return dataset
    
    #--------------------------------------------------------------------------
    def upsert_dataframe(self, df: pd.DataFrame, table_cls):
        table = table_cls.__table__
        session = self.Session()
        try:
            unique_cols = []
            for uc in table.constraints:
                if isinstance(uc, UniqueConstraint):
                    unique_cols = uc.columns.keys()
                    break
            if not unique_cols:
                raise ValueError(f"No unique constraint found for {table_cls.__name__}")

            # Batch insertions for speed
            records = df.to_dict(orient='records')
            for i in range(0, len(records), self.insert_batch_size):
                batch = records[i:i + self.insert_batch_size]
                stmt = insert(table).values(batch)
                # Columns to update on conflict
                update_cols = {c: getattr(stmt.excluded, c) for c in batch[0] if c not in unique_cols}
                stmt = stmt.on_conflict_do_update(
                    index_elements=unique_cols,
                    set_=update_cols
                )
                session.execute(stmt)
                session.commit()
            session.commit()
        finally:
            session.close()    

    #--------------------------------------------------------------------------
    def load_roulette_dataset(self):
        with self.engine.connect() as conn:
            data = pd.read_sql_table('ROULETTE_SERIES', conn)
            
        return data   
    
    #--------------------------------------------------------------------------
    def save_roulette_data(self, data : pd.DataFrame):
        with self.engine.begin() as conn:
            conn.execute(sqlalchemy.text(f"DELETE FROM ROULETTE_SERIES"))        
        data.to_sql("ROULETTE_SERIES", self.engine, if_exists='append', index=False) 
        
    #--------------------------------------------------------------------------
    def save_predicted_games(self, data : pd.DataFrame):         
        self.upsert_dataframe(data, PredictedGames)

    #--------------------------------------------------------------------------
    def save_checkpoints_summary(self, data : pd.DataFrame):         
        self.upsert_dataframe(data, CheckpointSummary)

        

    