from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, List
import pymongo
from bson import ObjectId
from pydantic import parse_obj_as
from datetime import datetime


application = FastAPI()

class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"

class InputPatients(BaseModel):
    sort_number: int
    name: str
    age: int
    gender: Gender
    contact_number: int

class JadwalKlinik(BaseModel):
    Tanggal: datetime
    Waktu_Mulai: str
    Waktu_Selesai: str
    DokterID: str
    Kapasitas: int

class JadwalKlinikInDB(JadwalKlinik):
    JadwalID: str

class UpdateJadwalKlinik(BaseModel):
    Tanggal: Optional[datetime] = None
    Waktu_Mulai: Optional[str] = None
    Waktu_Selesai: Optional[str] = None
    Kapasitas: Optional[int] = None

class StatusReservasi(str, Enum):
    Dikonfirmasi = "Dikonfirmasi"
    Dibatalkan = "Dibatalkan"
    MenungguKonfirmasi = "Menunggu Konfirmasi"

class Reservasi(BaseModel):
    PasienID: str
    JadwalID: str
    TanggalReservasi: datetime
    NomorAntrian: int
    StatusReservasi: StatusReservasi

class ReservasiInDB(Reservasi):
    ReservasiID: str

class UpdateReservasi(BaseModel):
    PasienID: Optional[str] = None
    JadwalID: Optional[str] = None
    TanggalReservasi: Optional[datetime] = None
    NomorAntrian: Optional[int] = None
    StatusReservasi: Optional[StatusReservasi] = None

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, model):
        return {"type": "string"}

class Patients(BaseModel):
    id: PyObjectId = Field(alias="_id")
    sort_number: int
    name: str
    age: int
    gender: Gender
    contact_number: int

class Config:
    json_encoders = {ObjectId: str}

client = pymongo.MongoClient("mongodb://localhost:27017")
db = client.get_database("clinic_db")
patients = db.get_collection("patients")
jadwal_klinik_collection = db.get_collection("jadwal_klinik")
reservasi_collection = db.get_collection("reservasi")

@application.post("/patients")
def create_patients(input_patients: InputPatients):
    patients_data = input_patients.dict()
    result = patients.insert_one(patients_data)
    inserted_id = str(result.inserted_id)
    return {"id": inserted_id, **patients_data}

# Pasien
@application.get("/patients")
def get_patients(sort_number: Optional[int] = None):
    if sort_number is not None:
        result_filter = list(patients.find({"sort_number": sort_number}))
    else:
        result_filter = list(patients.find())
    
    # Convert ObjectId to string for each document
    for r in result_filter:
        r["_id"] = str(r["_id"])
       
    return result_filter

@application.put("/patients/{sort_number}")
def update_patient_by_sort_number(sort_number: int, input_patient: InputPatients):
    # Update the patient data in the MongoDB collection based on sort number
    result = patients.update_one({"sort_number": sort_number}, {"$set": input_patient.dict()})

    if result.modified_count == 1:
        updated_patient = patients.find_one({"sort_number": sort_number})
        updated_patient["_id"] = str(updated_patient["_id"])
        return updated_patient
    else:
        raise HTTPException(status_code=404, detail="Patient not found")

@application.delete("/patients/{sort_number}")
def delete_patient_by_sort_number(sort_number: int):
    # Delete the patient from the MongoDB collection based on sort number
    result = patients.delete_one({"sort_number": sort_number})

    if result.deleted_count == 1:
        return {"status": "success", "message": "Patient deleted"}
    else:
        raise HTTPException(status_code=404, detail="Patient not found")

# Jadwal Klinik
# Create Jadwal Klinik
@application.post("/jadwal_klinik", response_model=JadwalKlinikInDB)
def create_jadwal_klinik(jadwal_klinik: JadwalKlinik):
    jadwal_klinik_data = jadwal_klinik.dict()
    result = jadwal_klinik_collection.insert_one(jadwal_klinik_data)
    inserted_id = str(result.inserted_id)
    return {"JadwalID": inserted_id, **jadwal_klinik_data}

# Read Jadwal Klinik
# Retrieve reservations for a specific clinic schedule
@application.get("/schedule_reservations/{jadwal_id}", response_model=List[ReservasiInDB])
def get_schedule_reservations(jadwal_id: str):
    schedule_reservations = reservasi_collection.find({"JadwalID": jadwal_id})
    result = [parse_obj_as(ReservasiInDB, res) for res in schedule_reservations]
    return result

# Update Jadwal Klinik
@application.put("/jadwal_klinik/{jadwal_id}", response_model=JadwalKlinikInDB)
def update_jadwal_klinik(jadwal_id: str, updated_data: UpdateJadwalKlinik):
    # Convert the jadwal_id to ObjectId
    obj_id = ObjectId(jadwal_id)

    # Update the Jadwal Klinik data in the MongoDB collection
    update_data = {k: v for k, v in updated_data.dict().items() if v is not None}
    result = jadwal_klinik_collection.update_one({"_id": obj_id}, {"$set": update_data})

    if result.modified_count == 1:
        updated_jadwal = jadwal_klinik_collection.find_one({"_id": obj_id})
        updated_jadwal["_id"] = str(updated_jadwal["_id"])
        return updated_jadwal
    else:
        raise HTTPException(status_code=404, detail="Jadwal Klinik not found")

# Delete Jadwal Klinik
@application.delete("/jadwal_klinik/{jadwal_id}", response_model=dict)
def delete_jadwal_klinik(jadwal_id: str):
    # Convert the jadwal_id to ObjectId
    obj_id = ObjectId(jadwal_id)

    # Delete the Jadwal Klinik from the MongoDB collection
    result = jadwal_klinik_collection.delete_one({"_id": obj_id})

    if result.deleted_count == 1:
        return {"status": "success", "message": "Jadwal Klinik deleted"}
    else:
        raise HTTPException(status_code=404, detail="Jadwal Klinik not found")

# Reservasi
# Create Reservasi
@application.post("/reservasi", response_model=ReservasiInDB)
def create_reservasi(reservasi: Reservasi):
    reservasi_data = reservasi.dict()
    result = reservasi_collection.insert_one(reservasi_data)
    inserted_id = str(result.inserted_id)
    return {"ReservasiID": inserted_id, **reservasi_data}

# Read Reservasi
@application.get("/patient_reservations/{patient_id}", response_model=List[ReservasiInDB])
def get_patient_reservations(patient_id: str):
    patient_reservations = reservasi_collection.find({"PasienID": patient_id})
    result = [parse_obj_as(ReservasiInDB, res) for res in patient_reservations]
    return result

# Update Reservasi
@application.put("/reservasi/{reservasi_id}", response_model=ReservasiInDB)
def update_reservasi(reservasi_id: str, updated_data: UpdateReservasi):
    # Convert the reservasi_id to ObjectId
    obj_id = ObjectId(reservasi_id)

    # Update the Reservasi data in the MongoDB collection
    update_data = {k: v for k, v in updated_data.dict().items() if v is not None}
    result = reservasi_collection.update_one({"_id": obj_id}, {"$set": update_data})

    if result.modified_count == 1:
        updated_reservasi = reservasi_collection.find_one({"_id": obj_id})
        updated_reservasi["_id"] = str(updated_reservasi["_id"])
        return updated_reservasi
    else:
        raise HTTPException(status_code=404, detail="Reservasi not found")

# Delete Reservasi
@application.delete("/reservasi/{reservasi_id}", response_model=dict)
def delete_reservasi(reservasi_id: str):
    # Convert the reservasi_id to ObjectId
    obj_id = ObjectId(reservasi_id)

    # Delete the Reservasi from the MongoDB collection
    result = reservasi_collection.delete_one({"_id": obj_id})

    if result.deleted_count == 1:
        return {"status": "success", "message": "Reservasi deleted"}
    else:
        raise HTTPException(status_code=404, detail="Reservasi not found")